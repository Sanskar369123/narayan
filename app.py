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
# Convert each row → text chunk for RAG
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
Price: {row.get('procurement_price')}
"""

car_texts = [row_to_text(row) for _, row in cars.iterrows()]


# ---------------------
# Embedding Function (OpenRouter)
# ---------------------
def embed_text(texts):
    url = "https://openrouter.ai/api/v1/embeddings"

    headers = {
        "Authorization": f"Bearer {st.secrets['OPENROUTER_API_KEY']}",
        "HTTP-Referer": "http://localhost:8501",
        "X-Title": "Spinny RAG Search"
    }

    payload = {
        "model": "openai/text-embedding-3-small",
        "input": texts,
    }

    response = requests.post(url, json=payload, headers=headers)
    data = response.json()

    return np.array([item["embedding"] for item in data["data"]]).astype("float32")


# ---------------------
# Build embeddings once
# ---------------------
@st.cache_resource
def build_embeddings():
    embeddings = embed_text(car_texts)
    return embeddings

car_embeddings = build_embeddings()


# ---------------------
# Cosine Similarity Search (NO FAISS)
# ---------------------
def cosine_similarity(a, b):
    a_norm = a / np.linalg.norm(a)
    b_norm = b / np.linalg.norm(b, axis=1, keepdims=True)
    return np.dot(b_norm, a_norm)


def search_car(query, k=5):
    query_vec = embed_text([query])[0]

    scores = cosine_similarity(query_vec, car_embeddings)

    top_k_idx = np.argsort(scores)[-k:][::-1]

    matched_texts = [car_texts[i] for i in top_k_idx]
    matched_rows = [cars.iloc[i] for i in top_k_idx]

    return matched_texts, matched_rows


# ---------------------
# LLM with RAG Context
# ---------------------
def ask_llm_with_context(user_query, context_blocks):
    url = "https://openrouter.ai/api/v1/chat/completions"

    context_str = "\n\n".join(context_blocks)

    system_prompt = f"""
You are Spinny AI.
Answer ONLY using the car data provided in the context below.
Do not invent any car details.
If the user asks something outside the context, answer using ONLY the provided cars.

CONTEXT:
{context_str}
"""

    payload = {
        "model": "z-ai/glm-4.5-air:free",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query}
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
st.title("🚗 Spinny AI — Car Advisor (RAG Powered)")
st.write("Ask anything about the cars in your dataset. Answers come ONLY from your CSV.")

query = st.chat_input("Try: 'Petrol Honda cars under 5 lakh in Delhi'")

if query:
    st.chat_message("user").write(query)

    # Step 1: RAG search → retrieve relevant cars
    context_blocks, rows = search_car(query, k=5)

    # Step 2: LLM uses only retrieved data
    llm_response = ask_llm_with_context(query, context_blocks)

    st.chat_message("assistant").write(llm_response)

    # Step 3: Show the retrieved cars used for answer
    st.subheader("🔎 Cars matched for this answer")
    st.dataframe(pd.DataFrame(rows))
