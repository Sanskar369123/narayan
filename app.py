import streamlit as st
import requests
import pandas as pd

# ---------------------
# Load car dataset
# ---------------------
@st.cache_data
def load_data():
    return pd.read_csv("cars.csv")

cars = load_data()

# ---------------------
# OpenRouter Call
# ---------------------
def ask_llm(messages):
    url = "https://openrouter.ai/api/v1"
    headers = {
        "Authorization": f"Bearer {st.secrets['OPENROUTER_API_KEY']}",
    }

    payload = {
        "model": "z-ai/glm-4.5-air:free",     # You can change model
        "messages": messages
    }

    response = requests.post(url, json=payload, headers=headers)
    return response.json()["choices"][0]["message"]["content"]

# ---------------------
# Streamlit UI
# ---------------------
st.title("🚗 Spinny AI — Car Advisor MVP")

st.write("Chat with the AI agent to find your perfect car!")

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": "You are Spinny AI, a car recommendation expert."},
        {"role": "assistant", "content": "Hi! I'm Spinny AI 😊\nTell me what kind of car you're looking for — or I can start by asking questions. Ready?"}
    ]

# Chat history
for msg in st.session_state.messages:
    if msg["role"] == "assistant":
        st.chat_message("assistant").write(msg["content"])
    elif msg["role"] == "user":
        st.chat_message("user").write(msg["content"])

# User input
user_input = st.chat_input("Type your question...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})

    llm_reply = ask_llm(st.session_state.messages)
    st.session_state.messages.append({"role": "assistant", "content": llm_reply})

    st.chat_message("assistant").write(llm_reply)

# -------------------------
# Optional car recommendation function
# -------------------------
def filter_cars(criteria):
    result = cars.copy()

    if "budget" in criteria:
        result = result[result["price"] <= criteria["budget"]]

    if "fuel" in criteria:
        result = result[result["fuel"].str.contains(criteria["fuel"], case=False)]

    if "body_type" in criteria:
        result = result[result["body_type"].str.contains(criteria["body_type"], case=False)]

    return result.head(5)
