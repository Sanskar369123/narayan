import streamlit as st
import requests
import base64

st.set_page_config(page_title="Spinny Mitra Voice", page_icon="🎤", layout="centered")

st.title("🎙️ Spinny Mitra – Voice Car Consultant")
st.caption("Speak to Spinny Mitra. Ask anything about buying a used car.")

# -------------------------
# OPENROUTER API
# -------------------------
API_KEY = st.secrets["OPENROUTER_API_KEY"]

def call_deepseek(query):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "HTTP-Referer": "spinny-mitra-voice",
        "X-Title": "Spinny Mitra Voice",
    }
    payload = {
        "model": "deepseek/deepseek-chat:free",
        "messages": [
            {"role": "system", "content": 
             "You are Spinny Mitra, a friendly and expert car consultant. "
             "Answer SHORT, helpful, and clear. Speak like Perplexity Voice. "
             "Do NOT show chain-of-thought. "
             "If needed, ask 1 follow-up question."},
            {"role": "user", "content": query}
        ]
    }

    r = requests.post(url, headers=headers, json=payload)
    return r.json()["choices"][0]["message"]["content"]

# -------------------------
# SPEECH → TEXT (Whisper)
# -------------------------
def transcribe_audio(audio_bytes):
    url = "https://openrouter.ai/api/v1/audio/transcriptions"
    headers = {"Authorization": f"Bearer {API_KEY}"}

    files = {
        "file": ("audio.wav", audio_bytes, "audio/wav"),
        "model": (None, "openai/whisper-large-v3"),
    }

    r = requests.post(url, headers=headers, files=files)
    return r.json()["text"]

# -------------------------
# TEXT → SPEECH
# -------------------------
def generate_voice(text):
    url = "https://openrouter.ai/api/v1/audio/speech"
    headers = {"Authorization": f"Bearer {API_KEY}"}
    payload = {
        "model": "openai/tts-1",
        "voice": "alloy",
        "input": text,
    }
    r = requests.post(url, headers=headers, json=payload)
    return r.content

# -------------------------
# UI
# -------------------------
st.markdown(
    """
    <style>
        .mic-container {
            margin-top: 40px;
            text-align: center;
        }
        .mic-button {
            width: 120px;
            height: 120px;
            background: #22c55e;
            border-radius: 50%;
            font-size: 60px;
            display: flex;
            justify-content: center;
            align-items: center;
            margin: auto;
            cursor: pointer;
            box-shadow: 0 0 30px rgba(10, 240, 100, 0.5);
        }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown('<div class="mic-container">', unsafe_allow_html=True)

audio = st.file_uploader("Click below & upload a short voice clip to talk to Mitra.", type=["wav", "mp3", "m4a"])

st.markdown('<div class="mic-button">🎤</div>', unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

if audio:
    st.info("🔍 Listening…")
    user_text = transcribe_audio(audio.read())
    st.success(f"🗣️ You said: **{user_text}**")

    st.info("💡 Thinking…")
    reply = call_deepseek(user_text)
    st.success(f"🤖 Mitra: {reply}")

    st.info("🔊 Speaking…")
    tts_audio = generate_voice(reply)

    st.audio(tts_audio, format="audio/mp3")

