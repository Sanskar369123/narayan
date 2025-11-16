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


# ---------------- SESSION STATE ----------------
if "messages" not in st.session_state:
    st.session_state.messages = []

if "prefs" not in st.session_state:
    st.session_state.prefs = {}

if "stage" not in st.session_state:
    st.session_state.stage = "greeting"


# ---------------- SYSTEM PROMPT ----------------
SYSTEM_PROMPT = """
You are an AI Car Buying Consultant who asks ONE QUESTION AT A TIME.

Stages:
greeting → ask_budget → ask_city → ask_usage → ask_fuel → ask_transmission → ask_priorities → ready_to_recommend

Rules:
- Ask ONLY ONE question at a time.
- Never list multiple questions.
- Move to the next stage only after the user responds.
- In ready_to_recommend, suggest 2–4 cars with pros/cons and reasoning.
- Stay friendly and short.

"""


# ---------------- LLM CALL ----------------
def call_openrouter(messages):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }

    data = {
        "model": "tngtech/deepseek-r1t2-chimera:free",
        "messages": messages,
        "temperature": 0.25,
    }

    response = requests.post(OPENROUTER_URL, headers=headers, data=json.dumps(data))

    if response.status_code != 200:
        return f"⚠️ OpenRouter Error: {response.text}"

    result = response.json()
    return result["choices"][0]["message"]["content"]


# ---------------- NEXT QUESTION LOGIC ----------------
def next_question():
    stage = st.session_state.stage

    if stage == "greeting":
        st.session_state.stage = "ask_budget"
        return "Hi! 👋 Let's find the perfect car for you. What's your budget range?"

    if stage == "ask_budget":
        st.session_state.stage = "ask_city"
        return "Great! Which city are you based in?"

    if stage == "ask_city":
        st.session_state.stage = "ask_usage"
        return "Nice! How do you mostly drive — city, highway, or mixed?"

    if stage == "ask_usage":
        st.session_state.stage = "ask_fuel"
        return "Got it! Do you prefer Petrol, Diesel, CNG, or Electric?"

    if stage == "ask_fuel":
        st.session_state.stage = "ask_transmission"
        return "Understood. Do you prefer Automatic or Manual?"

    if stage == "ask_transmission":
        st.session_state.stage = "ask_priorities"
        return "Thanks! What matters most to you: mileage, safety, comfort, features, or low maintenance?"

    if stage == "ask_priorities":
        st.session_state.stage = "ready_to_recommend"
        return None  # LLM will handle recommendation

    return None


# ---------------- UI ----------------
st.markdown("<h1 style='text-align:center;'>🚗 AI Car Buying Consultant</h1>", unsafe_allow_html=True)
st.write("Chat naturally — I’ll guide you one step at a time.")

# Render chat history FIRST
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# Input box
user_input = st.chat_input("Type your message...")

if user_input:
    # 1️⃣ Add USER message immediately
    st.session_state.messages.append({"role": "user", "content": user_input})

    # Display it instantly
    with st.chat_message("user"):
        st.write(user_input)

    # Save the preference to dict
    st.session_state.prefs[st.session_state.stage] = user_input

    # 2️⃣ Determine NEXT question
    question = next_question()

    # 3️⃣ If we still have questions → show next question (NO LLM)
    if question:
        st.session_state.messages.append({"role": "assistant", "content": question})
        with st.chat_message("assistant"):
            st.write(question)

    # 4️⃣ If stage = ready_to_recommend → CALL THE MODEL
    else:
        with st.chat_message("assistant"):
            with st.spinner("Finding the best cars for you..."):
                messages = [{"role": "system", "content": SYSTEM_PROMPT}] + st.session_state.messages
                reply = call_openrouter(messages)
                st.write(reply)

        st.session_state.messages.append({"role": "assistant", "content": reply})
