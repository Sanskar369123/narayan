import streamlit as st
import pandas as pd
import requests
import numpy as np
import re

# ---------------------
# Load + Normalize CSV
# ---------------------
@st.cache_data
def load_data():
    df = pd.read_csv("cars.csv")
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
# Convert car row -> text block
# ---------------------
def row_to_text(row):
    return f"""
Car ID: {row.get('lead')}
City: {row.get('city')}
Make: {row.get('make')}
Model: {row.get('model')}
Variant: {row.get('variant')}
Year: {row.get('make_year')}
Fuel: {row.get('fuel_type')}
Transmission: {row.get('transmission_type')}
Mileage: {row.get('mileage')} km
Ownership: {row.get('ownership')}
Price: ₹{row.get('procurement_price')}
"""

car_texts = [row_to_text(row) for _, row in cars.iterrows()]


# ---------------------
# FREE KEYWORD SCORING SEARCH
# ---------------------
def score_car(car_text, query):
    score = 0
    for word in query.lower().split():
        if word in car_text.lower():
            score += 1
    return score


def search_car(query, k=10):
    scores = [(score_car(text, query), i) for i, text in enumerate(car_texts)]
    scores.sort(reverse=True, key=lambda x: x[0])

    top_idx = [i for score, i in scores[:k] if score > 0]

    matched_texts = [car_texts[i] for i in top_idx]
    matched_rows = [cars.iloc[i] for i in top_idx]

    return matched_texts, matched_rows


# ---------------------
# LLM call (z-ai/glm-4.5-air:free)
# ---------------------
def call_llm(system_prompt, user_prompt):
    url = "https://openrouter.ai/api/v1/chat/completions"

    payload = {
        "model": "z-ai/glm-4.5-air:free",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    }

    headers = {
        "Authorization": f"Bearer {st.secrets['OPENROUTER_API_KEY']}",
        "HTTP-Referer": "http://localhost:8501",
        "X-Title": "Spinny Car Advisor"
    }

    response = requests.post(url, json=payload, headers=headers)
    data = response.json()

    return data["choices"][0]["message"]["content"]


# ---------------------
# Initialize conversational criteria
# ---------------------
if "criteria" not in st.session_state:
    st.session_state.criteria = {
        "budget": None,
        "city": None,
        "fuel": None,
        "transmission": None,
        "make": None
    }

if "stage" not in st.session_state:
    st.session_state.stage = "ask_budget"

if "messages" not in st.session_state:
    st.session_state.messages = []


# ---------------------
# Ask next question
# ---------------------
def ask_next_question():
    if st.session_state.stage == "ask_budget":
        return "What is your budget range?"
    if st.session_state.stage == "ask_city":
        return "Which city are you looking to buy the car in?"
    if st.session_state.stage == "ask_fuel":
        return "What fuel type do you prefer? (Petrol / Diesel / CNG)"
    if st.session_state.stage == "ask_transmission":
        return "What transmission type do you prefer? (Manual / Automatic)"
    if st.session_state.stage == "ask_make":
        return "Do you prefer any particular car brand? (Honda, Maruti, Hyundai, etc.)"
    return None


# ---------------------
# Extract details from user message
# ---------------------
def extract_answer(stage, user_input):
    text = user_input.lower()
    c = st.session_state.criteria

    if stage == "ask_budget":
        match = re.findall(r"(\d+)", text)
        if match:
            c["budget"] = match[0]  # store numeric value
            st.session_state.stage = "ask_city"
            return True

    if stage == "ask_city":
        c["city"] = text
        st.session_state.stage = "ask_fuel"
        return True

    if stage == "ask_fuel":
        if "petrol" in text:
            c["fuel"] = "petrol"
        elif "diesel" in text:
            c["fuel"] = "diesel"
        elif "cng" in text:
            c["fuel"] = "cng"
        st.session_state.stage = "ask_transmission"
        return True

    if stage == "ask_transmission":
        if "auto" in text:
            c["transmission"] = "automatic"
        else:
            c["transmission"] = "manual"
        st.session_state.stage = "ask_make"
        return True

    if stage == "ask_make":
        c["make"] = text
        st.session_state.stage = "search"
        return True

    return False


# ---------------------
# Streamlit UI
# ---------------------
st.title("🚗 Spinny AI — Personal Car Consultant")

# Display chat
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# Chat input
user_input = st.chat_input("Your answer...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})

    # Process answer
    extract_answer(st.session_state.stage, user_input)

    # Next stage?
    if st.session_state.stage != "search":
        question = ask_next_question()
        st.session_state.messages.append({"role": "assistant", "content": question})
        st.chat_message("assistant").write(question)

    else:
        # Build final search query
        c = st.session_state.criteria
        search_query = f"{c['budget']} budget {c['city']} {c['fuel']} {c['transmission']} {c['make']}"

        # Search cars
        context_blocks, rows = search_car(search_query, k=10)

        if len(rows) == 0:
            answer = "No matching cars found in your budget. Try changing your preferences."
        else:
            # LLM contextual answer
            context = "\n\n".join(context_blocks)
            answer = call_llm(
                system_prompt=f"You are a car advisor. Use ONLY this data:\n{context}",
                user_prompt="Recommend the best car from the above list."
            )

        st.session_state.messages.append({"role": "assistant", "content": answer})
        st.chat_message("assistant").write(answer)

        # Show matched cars
        st.subheader("🔎 Cars matched to your needs")
        st.dataframe(pd.DataFrame(rows))
