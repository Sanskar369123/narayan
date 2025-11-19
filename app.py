import streamlit as st
import pandas as pd
import requests
import textwrap
import base64
import tempfile
import os

# -------------------------------------------------------
# STREAMLIT CONFIG
# -------------------------------------------------------
st.set_page_config(
    page_title="Spinny Mitra – Voice & Perplexity",
    page_icon="🚗",
    layout="wide",
)

# -------------------------------------------------------
# DATA LOADING
# -------------------------------------------------------
@st.cache_data
def load_cars():
    return pd.read_csv("cars.csv")

cars_df = load_cars()

# -------------------------------------------------------
# OPENROUTER DEEPSEEK CALL (Same as your code)
# -------------------------------------------------------
def ask_deepseek(query: str, history, car_context: str) -> str:
    url = "https://openrouter.ai/api/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {st.secrets['OPENROUTER_API_KEY']}",
        "HTTP-Referer": "https://spinny-mitra-demo",
        "X-Title": "Spinny Mitra Voice",
        "Content-Type": "application/json",
    }

    system_prompt = """
    You are Spinny Mitra, an expert used-car consultant.
    Answer with friendly, clear advice. Use the given car data context.
    Provide short helpful insights and optionally car suggestions.
    """

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)

    user_content = f"""
    User question: {query}

    Relevant car context:
    {car_context}
    """

    messages.append({"role": "user", "content": user_content})

    payload = {
        "model": "deepseek/deepseek-chat:free",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 800,
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"].strip()


# -------------------------------------------------------
# SIMPLE RETRIEVAL FOR CONTEXT (Same as your code)
# -------------------------------------------------------
def filter_cars(query: str, max_rows: int = 10):
    df = cars_df.copy()
    q = query.lower()

    if "petrol" in q: df = df[df["Fuel Type"].str.contains("petrol", case=False)]
    if "diesel" in q: df = df[df["Fuel Type"].str.contains("diesel", case=False)]
    if "cng" in q:    df = df[df["Fuel Type"].str.contains("cng", case=False)]
    if "automatic" in q: df = df[df["Transmission Type"].str.contains("auto", case=False)]

    return df.head(max_rows)

def cars_to_context(df):
    if df.empty: return "No matching cars."
    cols = ["Make", "Model", "Variant", "Make Year", "Fuel Type", "Transmission Type", "Procurement Price"]
    lines = []
    for _, row in df[cols].iterrows():
        vals = ", ".join([f"{c}: {row[c]}" for c in cols])
        lines.append(vals)
    return "\n".join(lines)

# -------------------------------------------------------
# OPENROUTER WHISPER ASR (Speech to Text)
# -------------------------------------------------------
def transcribe_audio(file_bytes):
    url = "https://openrouter.ai/api/v1/audio/transcriptions"
    headers = {
        "Authorization": f"Bearer {st.secrets['OPENROUTER_API_KEY']}",
    }

    files = {
        "file": ("audio.wav", file_bytes, "audio/wav"),
        "model": (None, "openai/whisper-large-v3"),
    }

    resp = requests.post(url, headers=headers, files=files)
    resp.raise_for_status()
    data = resp.json()
    return data["text"]

# -------------------------------------------------------
# OPENROUTER TTS (LLM -> spoken voice)
# -------------------------------------------------------
def speak_text(text):
    url = "https://openrouter.ai/api/v1/audio/speech"

    headers = {
        "Authorization": f"Bearer {st.secrets['OPENROUTER_API_KEY']}",
    }

    payload = {
        "model": "openai/tts-1",
        "voice": "alloy",
        "input": text,
    }

    resp = requests.post(url, headers=headers, json=payload)
    resp.raise_for_status()
    audio_bytes = resp.content

    return audio_bytes

# -------------------------------------------------------
# UI LAYOUT
# -------------------------------------------------------
st.markdown("""
<style>
.avatar-container {
    width: 420px;
    height: 650px;
    border-radius: 30px;
    background: #0b0f17;
    padding: 20px;
    box-shadow: 0 0 50px rgba(0,0,0,0.6);
    position: relative;
    margin:auto;
}

.orb {
    width: 250px;
    height: 250px;
    border-radius: 50%;
    background: radial-gradient(circle at 30% 20%, #4da9ff, #0055ff, #001a4d);
    margin: auto;
    margin-top: 40px;
    animation: float 4s ease-in-out infinite;
    box-shadow: 0 0 60px rgba(0,100,255,0.5);
}

@keyframes float {
  0% { transform: translateY(0); }
  50% { transform: translateY(-14px); }
  100% { transform: translateY(0); }
}

.mic-btn {
    width: 80px;
    height: 80px;
    background: #22c55e;
    border-radius: 50%;
    color: #032d1a;
    font-size: 30px;
    border: none;
    margin: auto;
    margin-top: 30px;
    box-shadow: 0 0 30px rgba(0,255,100,0.5);
}

</style>
""", unsafe_allow_html=True)

left, right = st.columns([1.3, 1])

with left:
    st.subheader("🎙️ Spinny Mitra – Voice Avatar")

    st.markdown('<div class="avatar-container">', unsafe_allow_html=True)
    st.markdown('<div class="orb"></div>', unsafe_allow_html=True)

    audio_input = st.file_uploader("Speak to Spinny Mitra", type=["wav", "mp3", "m4a"])

    if audio_input:
        st.info("Transcribing your voice…")
        text = transcribe_audio(audio_input.read())

        st.success(f"You said: **{text}**")

        car_ctx_df = filter_cars(text)
        car_context = cars_to_context(car_ctx_df)

        response = ask_deepseek(text, [], car_context)

        st.markdown("### Mitra says:")
        st.write(response)

        # TTS playback
        st.info("Generating voice…")
        audio_data = speak_text(response)

        st.audio(audio_data, format="audio/mp3")

    st.markdown("</div>", unsafe_allow_html=True)

# RIGHT PANEL
with right:
    st.subheader("🔎 Recently matched cars")
    if "ctx_df" in locals():
        st.dataframe(car_ctx_df)
    else:
        st.info("Speak something to see matches.")
