import streamlit as st
import requests
import pandas as pd
import re

# ---------------------
# Load car dataset
# ---------------------
@st.cache_data
def load_data():
    return pd.read_csv("cars.csv")

cars = load_data()

# Initialize criteria store
if "criteria" not in st.session_state:
    st.session_state.criteria = {
        "budget_min": None,
        "budget_max": None,
        "city": None,
        "fuel": None,
        "transmission": None,
        "make": None,
    }

# ---------------------
# Filter Cars Function
# ---------------------
def filter_cars():
    df = cars.copy()

    c = st.session_state.criteria

    if c["budget_min"] and c["budget_max"]:
        df = df[
            (df["Procurement Price"] >= c["budget_min"]) &
            (df["Procurement Price"] <= c["budget_max"])
        ]

    if c["city"]:
        df = df[df["City"].str.contains(c["city"], case=False, na=False)]

    if c["fuel"]:
        df = df[df["Fuel Type"].str.contains(c["fuel"], case=False)]

    if c["transmission"]:
        df = df[df["Transmission Type"].str.contains(c["transmission"], case=False)]

    if c["make"]:
        df = df[df["Make"].str.contains(c["make"], case=False)]

    return df.head(10)


# ---------------------
# OpenRouter Call
# ---------------------
def ask_llm(messages):
    url = "https://openrouter.ai/api/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {st.secrets['OPENROUTER_API_KEY']}",
        "HTTP-Referer": "http://localhost:8501",
        "X-Title": "Spinny AI Car Advisor"
    }

    payload = {
        "model": "qwen/qwen-turbo",
        "messages": messages
    }

    response = requests.post(url, json=payload, headers=headers)
    data = response.json()
    return data["choices"][0]["message"]["content"]


# ---------------------
# Streamlit UI
# ---------------------
st.title("🚗 Spinny AI — Car Advisor MVP")
st.write("Chat with the AI agent to find your perfect car!")

# Chat history
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": """
You are Spinny AI. 
Your job is to help users pick the right used car.

RULES:
- Ask ONE question at a time.
- Collect these 5 details in order:
  1. Budget
  2. City
  3. Fuel type
  4. Transmission
  5. Car make preference
- After all 5 are collected, say: "Great! Let me fetch the best cars for you."
- Do NOT recommend cars yourself.
"""},
        {"role": "assistant", "content": "Hi! I’m Spinny AI 😊 Let's find a perfect car for you. What is your budget range?"}
    ]

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# ---------------------
# Extract user preferences automatically
# ---------------------
def extract_criteria(text):
    c = st.session_state.criteria

    # Budget detection (like “4-6 lakhs”)
    budget_match = re.findall(r"(\d+)\s*[-to]+\s*(\d+)", text)
    if budget_match:
        low, high = budget_match[0]
        c["budget_min"] = int(low) * 100000
        c["budget_max"] = int(high) * 100000

    # City
    for city in cars["City"].unique():
        if city.lower() in text.lower():
            c["city"] = city

    # Fuel
    for f in ["petrol", "diesel", "cng", "electric"]:
        if f in text.lower():
            c["fuel"] = f

    # Transmission
    for t in ["automatic", "manual"]:
        if t in text.lower():
            c["transmission"] = t

    # Make
    for make in cars["Make"].unique():
        if make.lower() in text.lower():
            c["make"] = make


# ---------------------
# Handle Chat Input
# ---------------------
user_input = st.chat_input("Type your reply…")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})

    extract_criteria(user_input)

    # If all criteria collected → show cars
    if all(st.session_state.criteria.values()):
        st.chat_message("assistant").write("Great! Let me fetch the best cars for you 🚗")
        results = filter_cars()
        st.dataframe(results)
    else:
        # Otherwise ask next question via LLM
        reply = ask_llm(st.session_state.messages)
        st.session_state.messages.append({"role": "assistant", "content": reply})
        st.chat_message("assistant").write(reply)
