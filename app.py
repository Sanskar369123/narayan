import streamlit as st
import pandas as pd
import requests
import textwrap
import base64
import io
from gtts import gTTS
import pygame
import tempfile
import os

# ------------- CONFIG -------------
st.set_page_config(
    page_title="Spinny Mitra – Car Perplexity",
    page_icon="🚗",
    layout="wide",
)

# Initialize pygame mixer for audio playback
pygame.mixer.init()

# ------------- DATA LOADING -------------
@st.cache_data
def load_cars():
    return pd.read_csv("cars.csv")

cars_df = load_cars()

# ------------- TEXT-TO-SPEECH FUNCTIONS -------------
def text_to_speech(text, language='en', slow=False):
    """
    Convert text to speech using gTTS and return audio data
    """
    try:
        tts = gTTS(text=text, lang=language, slow=slow)
        audio_buffer = io.BytesIO()
        tts.write_to_fp(audio_buffer)
        audio_buffer.seek(0)
        return audio_buffer
    except Exception as e:
        st.error(f"Text-to-speech error: {e}")
        return None

def play_audio(audio_buffer):
    """
    Play audio from BytesIO buffer using pygame
    """
    try:
        # Save to temporary file and play
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
            tmp_file.write(audio_buffer.getvalue())
            tmp_file.flush()
            
            pygame.mixer.music.load(tmp_file.name)
            pygame.mixer.music.play()
            
            # Wait for playback to finish
            while pygame.mixer.music.get_busy():
                pygame.time.wait(100)
                
            # Clean up
            os.unlink(tmp_file.name)
            
    except Exception as e:
        st.error(f"Audio playback error: {e}")

def autoplay_audio(audio_buffer):
    """
    Create an autoplay audio element for Streamlit
    """
    audio_bytes = audio_buffer.getvalue()
    b64 = base64.b64encode(audio_bytes).decode()
    md = f"""
        <audio autoplay>
        <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
        </audio>
        """
    st.markdown(md, unsafe_allow_html=True)

# ------------- OPENROUTER / DEEPSEEK CALL -------------
def ask_deepseek(query: str, history, car_context: str) -> str:
    """
    Call DeepSeek via OpenRouter and return assistant's reply.
    """
    url = "https://openrouter.ai/api/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {st.secrets['OPENROUTER_API_KEY']}",
        "HTTP-Referer": "https://spinny-mitra-demo",
        "X-Title": "Spinny Mitra Car Perplexity",
        "Content-Type": "application/json",
    }

    system_prompt = textwrap.dedent("""
        You are **Spinny Mitra**, an expert used-car consultant for Spinny.

        GOAL:
        - Help users choose the right used car for their needs.
        - Use the provided car data context when answering.
        - Think like Perplexity: structured, clear, helpful, but don't show your reasoning steps.

        STYLE:
        - Friendly, concise, confident.
        - Explain *why* a car or fuel type is a good fit.
        - Offer to compare options if user is confused.
        - If the answer depends on their needs (budget, city, usage, family size), ask 1–2 clarifying questions.
        - Never invent spinny processes or prices not present in context; speak in approximate ranges instead.

        OUTPUT FORMAT:
        - Short overview (2–3 sentences).
        - Then bullet points for key reasoning.
        - If relevant cars are provided, mention 2–5 good fits and why.
    """)

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)

    user_content = f"""
    User question: {query}

    Relevant Spinny car data (sample rows, not exhaustive):
    {car_context}

    Please answer using the above data when relevant. 
    Do NOT show any chain-of-thought or step-by-step reasoning, 
    just the final explanation.
    """
    messages.append({"role": "user", "content": user_content})

    payload = {
        "model": "tngtech/deepseek-r1t2-chimera:free",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 800,
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"].strip()

# ------------- SIMPLE CAR RETRIEVAL -------------
def filter_cars(query: str, max_rows: int = 10) -> pd.DataFrame:
    """
    Very simple heuristic filter
    """
    df = cars_df.copy()
    q_lower = query.lower()

    # Fuel type heuristic
    fuel_map = {
        "petrol": "petrol",
        "diesel": "diesel",
        "cng": "cng",
        "hybrid": "hybrid",
        "electric": "electric",
        "ev": "electric",
    }
    for word, ft in fuel_map.items():
        if word in q_lower and "Fuel Type" in df.columns:
            df = df[df["Fuel Type"].str.lower().str.contains(ft, na=False)]
            break

    # Transmission heuristic
    if "automatic" in q_lower and "Transmission Type" in df.columns:
        df = df[df["Transmission Type"].str.lower().str.contains("auto", na=False)]
    elif "manual" in q_lower and "Transmission Type" in df.columns:
        df = df[df["Transmission Type"].str.lower().str.contains("man", na=False)]

    # Budget detection
    import re
    budget_match = re.search(r"(\d+)\s*(lakh|lac|lk)", q_lower)
    if budget_match and "Procurement Price" in df.columns:
        lakhs = int(budget_match.group(1))
        rupees = lakhs * 100000
        df = df[df["Procurement Price"] <= rupees]

    # City heuristic
    if "City" in df.columns:
        for city in df["City"].dropna().unique():
            if str(city).lower() in q_lower:
                df = df[df["City"].str.lower() == str(city).lower()]
                break

    return df.head(max_rows)

def cars_to_context(df: pd.DataFrame) -> str:
    """
    Turn a small cars dataframe into a compact text table for the model.
    """
    if df.empty:
        return "No specific cars matched; you can answer more generally."

    cols = [c for c in df.columns if c in [
        "City", "Make", "Model", "Variant",
        "Make Year", "Fuel Type", "Transmission Type",
        "Mileage", "Ownership", "Procurement Price"
    ]]
    df_small = df[cols].copy()

    lines = []
    header = " | ".join(cols)
    lines.append(header)
    lines.append("-" * len(header))
    for _, row in df_small.iterrows():
        vals = [str(row[c]) for c in cols]
        lines.append(" | ".join(vals))
    return "\n".join(lines)

# ------------- VOICE AVATAR UI -------------
def voice_avatar_controls():
    """
    Add voice control options to sidebar
    """
    st.sidebar.markdown("---")
    st.sidebar.subheader("🎙️ Voice Avatar Settings")
    
    # Voice settings
    voice_enabled = st.sidebar.checkbox("Enable Voice Avatar", value=True)
    auto_play = st.sidebar.checkbox("Auto-play responses", value=False)
    voice_speed = st.sidebar.select_slider(
        "Voice Speed",
        options=["Slow", "Normal", "Fast"],
        value="Normal"
    )
    
    return voice_enabled, auto_play, voice_speed

# ------------- MAIN UI -------------
st.title("🚗 Spinny Mitra – Car Perplexity with Voice Avatar")

st.caption(
    "Ask anything about used cars – budget, city, fuel type, safety, comparison, EMI, etc. "
    "Spinny Mitra will answer like Perplexity, using Spinny-style car data as context."
)

# Voice avatar controls
voice_enabled, auto_play, voice_speed = voice_avatar_controls()

# Main layout
col_chat, col_cars = st.columns([2.2, 1.3])

with col_chat:
    # Initialize session state
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "audio_buffers" not in st.session_state:
        st.session_state.audio_buffers = {}

    # Display chat history with voice controls
    for i, msg in enumerate(st.session_state.chat_history):
        if msg["role"] == "user":
            with st.chat_message("user"):
                st.markdown(msg["content"])
        else:
            with st.chat_message("assistant"):
                st.markdown(msg["content"])
                
                # Add voice play button for assistant messages
                if voice_enabled and i in st.session_state.audio_buffers:
                    col1, col2 = st.columns([1, 4])
                    with col1:
                        if st.button("🔊 Play Voice", key=f"play_{i}"):
                            audio_buffer = st.session_state.audio_buffers[i]
                            play_audio(audio_buffer)
                    with col2:
                        st.caption("Click to hear the response")

    # Chat input
    user_query = st.chat_input("Ask Spinny Mitra anything about cars...")

    if user_query:
        # Add user message to state
        st.session_state.chat_history.append(
            {"role": "user", "content": user_query}
        )

        # Retrieve cars & build context
        ctx_df = filter_cars(user_query, max_rows=12)
        ctx_text = cars_to_context(ctx_df)

        with st.chat_message("assistant"):
            with st.spinner("Thinking like Perplexity…"):
                try:
                    answer = ask_deepseek(
                        query=user_query,
                        history=st.session_state.chat_history[:-1],
                        car_context=ctx_text,
                    )
                except Exception as e:
                    answer = f"Sorry, I ran into an error talking to the model: `{e}`"

                st.markdown(answer)
                
                # Generate and store audio
                if voice_enabled:
                    with st.spinner("Generating voice..."):
                        slow_speed = (voice_speed == "Slow")
                        audio_buffer = text_to_speech(answer, slow=slow_speed)
                        
                        if audio_buffer:
                            # Store audio buffer
                            msg_index = len(st.session_state.chat_history)
                            st.session_state.audio_buffers[msg_index] = audio_buffer
                            
                            # Auto-play if enabled
                            if auto_play:
                                st.info("🔊 Playing voice response...")
                                play_audio(audio_buffer)
                            
                            # Show play button
                            col1, col2 = st.columns([1, 4])
                            with col1:
                                if st.button("🔊 Play Again", key=f"play_again_{msg_index}"):
                                    play_audio(audio_buffer)
                            with col2:
                                st.caption("Voice response ready")

        # Add assistant response to history
        st.session_state.chat_history.append(
            {"role": "assistant", "content": answer}
        )

with col_cars:
    st.subheader("📊 Cars used as context")
    if st.session_state.chat_history:
        last_user = next(
            (m for m in reversed(st.session_state.chat_history) if m["role"] == "user"),
            None,
        )
        if last_user:
            ctx_df = filter_cars(last_user["content"], max_rows=30)
            if ctx_df.empty:
                st.info("No specific matches found. Showing random sample.")
                st.dataframe(cars_df.sample(min(10, len(cars_df))))
            else:
                st.dataframe(ctx_df)
    else:
        st.info("Ask a question to see relevant cars here.")

# Footer with voice instructions
st.sidebar.markdown("---")
st.sidebar.info(
    "**Voice Avatar Tips:**\n"
    "- Enable 'Auto-play' to hear responses automatically\n"
    "- Use 'Voice Speed' to adjust speaking pace\n"
    "- Click 'Play Voice' buttons to replay any response"
)
