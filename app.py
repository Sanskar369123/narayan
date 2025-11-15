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
# Convert row -> text block
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
Mileage: {row.get('mileage')}
Ownership: {row.get('ownership')}
Price: {row.get('procurement_price')}
"""

car_texts = [row_to_text(row) for _, row in cars.iterrows()]


# ---------------------
# Simple keyword-based scoring (FREE — no embeddings)
# ---------------------
def score_car(car_text, query):
    score = 0
    words = query.lower().split()

    for w in words:
        if w in car_text.lower():
            score += 1

    return score


def search_car(query, k=5):
    scores = [(score_car(text, query), i) for i, text in enumerate(car_texts)]
    scores.sort(reverse=True, key=lambda x: x[0])

    top_idx = [i for score, i in scores[:k] if score > 0]

    matched_texts = [car_texts[i] for i in top_idx]
    matched_rows = [cars.iloc[i] for i in top_idx]

    return matched_texts, matched_rows


# ---------------------
# LLM with RAG context
# ---------------------
def ask_llm_with_context(query, context_blocks):
    url = "https://openrouter.ai/api/v1/chat/completions"

    context_str = "\n\n".join(context_blocks)

    system_prompt = f"""
You are Spinny AI.
Answer ONLY using the cars listed in the context below.
If the user asks something that cannot be answered using the car list, say:
"I can only answer using the available cars."

CONTEXT:
{context_str}
"""

    payload = {
        "model": "z-ai/glm-4.5-air:free",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]
    }

    headers = {
        "Authorization": f"Bearer {st.secrets['OPENROUTER_API_KEY']}",
        "HTTP-Referer": "http://localhost:8501",
        "X-Title": "Spinny Car RAG"
    }

    response = requests.post(url, json=payload, headers=headers)
    data = response.json()

    return data["choices"][0]["message"]["content"]


# ---------------------
# Streamlit UI
# ---------------------
st.title("🚗 Spinny AI — Car Advisor (RAG, No Embeddings, 100% Free)")
st.write("Ask questions — AI will answer ONLY using your CSV data.")

query = st.chat_input("Try: 'Honda petrol cars under 5 lakh in Delhi'")

if query:
    st.chat_message("user").write(query)

    # Search cars
    context_blocks, rows = search_car(query, k=5)

    if len(context_blocks) == 0:
        st.chat_message("assistant").write(
            "No relevant cars found in the dataset. Try different keywords."
        )
    else:
        # LLM answer using the matched cars
        llm_response = ask_llm_with_context(query, context_blocks)
        st.chat_message("assistant").write(llm_response)

        st.subheader("🔎 Cars used to answer your question")
        st.dataframe(pd.DataFrame(rows))
