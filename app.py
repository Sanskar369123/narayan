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
    st.session_state.stage = "greeting"  # the conversation stage

# ---------------- SYSTEM PROMPT ----------------
SYSTEM_PROMPT = """
You are an AI Car Buying Consultant who asks ONE QUESTION AT A TIME.

RULES:
1. NEVER list multiple questions together.
2. ALWAYS ask only the NEXT required question.
3. Progress through these stages in order:

   greeting → ask_budget → ask_city → ask_usage → ask_fuel → ask_transmission → ask_priorities → ready_to_recommend

4. Once in 'ready_to_recommend', give 2–4 car suggestions with:
   - segment
   - pros
   - cons
   - why it fits the user's needs
5. Continue the conversation naturally after recommending.

IMPORTANT:
- If user answers, move to next stage.
- If user deviates, gently pull them back.
- Keep responses short, friendly, and conversational.
"""


# ---------------- HELPER FUNCTION ----------------
def call_openrouter(messages):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
        "HTTP-Referer": "https://your-app",
        "X-Title": "Car Advisor",
    }

    data = {
        "model": "tngtech/deepseek-r1t2-chimera:free",
        "messages": messages,
        "temperature": 0.3,
    }

    response = requests.post(OPENROUTER_URL, headers=headers, data=json.dumps(data))

    if response.status_code != 200:
        return f"Error: {response.text}"

    result = response.json()
    return result["choices"][0]["message"]["content"]


# ---------------- NEXT QUESTION LOGIC ----------------
def get_next_prompt():

    stage = st.session_state.stage
    prefs = st.session_state.prefs

    if stage == "greeting":
        st.session_state.stage = "ask_budget"
        return "Hi! 👋 Let's find the perfect car for you. What's your budget range?"

    if stage == "ask_budget":
        st.session_state.stage = "ask_city"
        return "Great! Which city are you based in?"

    if stage == "ask_city":
        st.session_state.stage = "ask_usage"
        return "Nice! How do you mostly drive? City, highway, or mixed?"

    if stage == "ask_usage":
        st.session_state.stage = "ask_fuel"
        return "Got it. Do you prefer Petrol, Diesel, CNG, or Electric?"

    if stage == "ask_fuel":
        st.session_state.stage = "ask_transmission"
        return "Understood. Do you want Automatic or Manual transmission?"

    if stage == "ask_transmission":
        st.session_state.stage = "ask_priorities"
        return "Thanks! What matters most to you: mileage, safety, comfort, features, or low maintenance?"

    if stage == "ask_priorities":
        st.session_state.stage = "ready_to_recommend"
        return "Perfect! Give me a moment while I shortlist the best options for you. 🚗💡"

    if stage == "ready_to_recommend":
        return None  # LLM will handle this stage

    return None


# ---------------- UI ----------------
st.title("🚗 AI Car Buying Consultant")

# Show chat history
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

user_input = st.chat_input("Your message...")

if user_input:

    # Add user message
    st.session_state.messages.append({"role": "user", "content": user_input})

    # Save user preferences (very raw)
    st.session_state.prefs[st.session_state.stage] = user_input

    # Determine next question
    next_q = get_next_prompt()

    # If next_q None → use LLM to recommend
    if next_q is None:
        with st.chat_message("assistant"):
            with st.spinner("Finding the best cars for you..."):
                messages = [{"role": "system", "content": SYSTEM_PROMPT}] + st.session_state.messages
                reply = call_openrouter(messages)

                st.markdown(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply})

    else:
        with st.chat_message("assistant"):
            st.markdown(next_q)
            st.session_state.messages.append({"role": "assistant", "content": next_q})
