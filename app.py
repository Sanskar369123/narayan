import streamlit as st
import requests
import pandas as pd
import re

# ---------------------
# Load / Normalize car dataset
# ---------------------
@st.cache_data
def load_data():
    df = pd.read_csv("cars.csv")

    # Normalize column names: city → city, Fuel Type → fuel_type, etc.
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
        .str.replace("\ufeff", "", regex=False)
    )

    return df

cars = load_data()


# ---------------------
# Initialize user criteria
# ---------------------
if "criteria" not in st.session_state:
    st.session_state.criteria = {
        "budget_min": None,
        "budget_max": None,
        "city": None,
        "fuel_type": None,
        "transmission_type": None,
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
            (df["procurement_price"] >= c["budget_min"]) &
            (df["procurement_price"] <= c["budget_max"])
        ]

    if c["city"]:
        df = df[df["city"].str.contains(c["city"], case=False, na=False)]

    if c["fuel_type"]:
        df = df[df["fuel_type"].str.contains(c["fuel_type"], case=False, na=False)]

    if c["transmission_type"]:
        df = df[df["transmission_type"].str.contains(c["transmission_type"], case=False, na=False)]

    if c["make"]:
        df = df[df["make"].str.contains(c["make"], case=False, na=False)]

    return df.head(10)


# ---------------------
# LLM API Call (OpenRouter)
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
# Extract Criteria from User Text
# ---------------------
def extract_criteria(text):
    text = text.lower()
    c = st.session_state.criteria

    # Budget pattern: "4-6 lakhs" or "4 to 6 lakh"
    budget_match = re.findall(r"(\d+)\s*[-to]+\s*(\d+)", text)
    if budget_match:
        low, high = budget_match[0]
        c["budget_min"] = int(low) * 100000
        c["budget_max"] = int(high) * 100000

    # City
    if "city" in cars.columns:
        for city in cars["city"].dropna().unique():
            if city.lower() in text:
                c["city"] = city

    # Fuel type
    for f in ["petrol", "diesel", "cng", "electric"]:
        if f in text:
            c["fuel_type"] = f

    # Transmission
    for t in ["automatic", "manual"]:
        if t in text:
            c["transmission_type"] = t

    # Make (Honda, Hyundai, etc.)
    if "make" in cars.columns:
        for make in cars["make"].dropna().unique():
            if make.lower() in text:
                c["make"] = make


# ---------------------
# Streamlit UI
# ---------------------
st.title("🚗 Spinny AI — Car Advisor MVP")
st.write("Chat with the AI agent to find your perfect car!")

# Chat history
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "system",
            "content": """
You are Spinny AI.

Ask ONE question at a time.
Collect these in order:
1. Budget
2. City
3. Fuel type
4. Transmission type
5. Car make preference

Do NOT recommend cars yourself. 
When all 5 are collected, say: "Great! Let me fetch the best cars for you."
"""
        },
        {
            "role": "assistant",
            "content": "Hi! I’m Spinny AI 😊 Let's find your perfect car. What is your budget range?"
        }
    ]

# Display only assistant & user messages (clean UI)
for msg in st.session_state.messages:
    if msg["role"] in ["assistant", "user"]:
        st.chat_message(msg["role"]).write(msg["content"])


# ---------------------
# User Input Handler
# ---------------------
user_input = st.chat_input("Type your reply...")

if user_input:
    # Add user message to conversation
    st.session_state.messages.append({"role": "user", "content": user_input})

    # Extract criteria
    extract_criteria(user_input)

    # If all 5 questions answered → show results
    c = st.session_state.criteria
    if all(c.values()):
        st.chat_message("assistant").write("Great! Let me fetch the best cars for you 🚗")

        results = filter_cars()

        if len(results) == 0:
            st.error("No cars found matching your preferences 😢")
        else:
            st.success("Here are your best matches:")
            st.dataframe(results)

    else:
        # Otherwise, ask next question
        reply = ask_llm(st.session_state.messages)
        st.session_state.messages.append({"role": "assistant", "content": reply})
        st.chat_message("assistant").write(reply)
