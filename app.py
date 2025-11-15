import streamlit as st
import pandas as pd
import requests
import numpy as np
import faiss
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
# Convert each row → text chunk
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
# Embedding function (OpenRouter)
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
# Create embeddings and FAISS index
# ---------------------
@st.cache_resource
def build_faiss():
    embeddings = embed_text(car_texts)

    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)

    return index, embeddings


index, embeddings = build_faiss()


# ---------------------
# Search most relevant cars
# ---------------------
def search_car(query, k=5):
    query_embed = embed_text([query])[0].reshape(1, -1)
    distances, results = index.search(query_embed, k)

    matched_texts = [car_texts[i] for i in results[0]]
    matched_rows = [cars.iloc[i] for i in results[0]]

    return matched_texts, matched_rows


# ---------------------
# LLM call with context-injection
# ---------------------
def ask_llm_with_context(user_query, context_blocks):
    url = "https://openrouter.ai/api/v1/chat/completions"

    context_str = "\n\n".join(context_blocks)

    system_prompt = f"""
You are Spinny AI.
Answer ONLY using the car data provided below.
Never invent information.
Never reference cars that are not included in the context.

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
st.write("Ask anything about cars in your dataset — I will answer ONLY from your CSV.")

query = st.chat_input("Ask something like: 'Petrol Honda cars under 5 lakh in Delhi'")

if query:
    st.chat_message("user").write(query)

    # Step 1: RAG Search
    context_blocks, rows = search_car(query, k=5)

    # Step 2: Answer using LLM with context
    llm_answer = ask_llm_with_context(query, context_blocks)

    st.chat_message("assistant").write(llm_answer)

    # Step 3: Show retrieved cars
    st.subheader("🔎 Cars considered for this answer")
    st.dataframe(pd.DataFrame(rows))
