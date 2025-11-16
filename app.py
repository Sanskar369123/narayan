import os
import streamlit as st
import requests
import json

# ---------------- CONFIG ----------------
st.set_page_config(page_title="AI Car Buying Consultant", page_icon="🚗")

API_KEY = st.secrets.get("OPENROUTER_API_KEY", None) or os.getenv("OPENROUTER_API_KEY")
if not API_KEY:
    st.error("❌ OPENROUTER_API_KEY not set.")
    st.stop()

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

SYSTEM_PROMPT = """
You are an expert Indian car buying consultant...
(keep your same prompt here)
"""

# ---------------- SESSION ----------------
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Hi! 👋 I’m your AI car consultant. Tell me your budget, city, and driving habits."
        }
    ]

# ---------------- UI ----------------
st.title("🚗 AI Car Buying Consultant")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Reset
if st.button("🔁 Reset"):
    st.session_state.messages = [
        {"role": "assistant", "content": "Reset complete. Tell me your needs again."}
    ]
    st.experimental_rerun()

# ---------------- LLM CALL USING REST API ----------------
def call_openrouter(messages):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
        "HTTP-Referer": "https://your-app",
        "X-Title": "Spinny Car Advisor"
    }

    data = {
        "model": "tngtech/deepseek-r1t2-chimera:free",
        "messages": messages,
        "temperature": 0.5
    }

    response = requests.post(
        OPENROUTER_URL,
        headers=headers,
        data=json.dumps(data)
    )

    if response.status_code != 200:
        return f"Error from OpenRouter: {response.text}"

    result = response.json()
    return result["choices"][0]["message"]["content"]

# ---------------- HANDLE INPUT ----------------
user_input = st.chat_input("Tell me your needs...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            ai_reply = call_openrouter(
                [{"role": "system", "content": SYSTEM_PROMPT}] + st.session_state.messages
            )
            st.markdown(ai_reply)

    st.session_state.messages.append({"role": "assistant", "content": ai_reply})
