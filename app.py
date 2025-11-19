import streamlit as st
import pandas as pd
import requests
import textwrap

# ------------- CONFIG -------------
st.set_page_config(
    page_title="Spinny Mitra – Car Perplexity",
    page_icon="🚗",
    layout="wide",
)

# ------------- DATA LOADING -------------
@st.cache_data
def load_cars():
    # Your CSV columns (example):
    # Lead,City,Current Category,Make,Model,Variant,Make Year,
    # Fuel Type,Transmission Type,Mileage,Ownership,Procurement Price
    return pd.read_csv("cars.csv")

cars_df = load_cars()

# ------------- OPENROUTER / DEEPSEEK CALL -------------
def ask_deepseek(query: str, history, car_context: str) -> str:
    """
    Call DeepSeek via OpenRouter and return assistant's reply.
    `history` is a list of {role, content} for previous turns.
    `car_context` is a string with relevant car rows.
    """
    url = "https://openrouter.ai/api/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {st.secrets['OPENROUTER_API_KEY']}",
        "HTTP-Referer": "https://spinny-mitra-demo",  # any identifier
        "X-Title": "Spinny Mitra Car Perplexity",
        "Content-Type": "application/json",
    }

    system_prompt = textwrap.dedent("""
        You are **Spinny Mitra**, an expert used-car consultant for Spinny.

        GOAL:
        - Help users choose the right used car for their needs.
        - Use the provided car data context when answering.
        - Think like Perplexity: structured, clear, helpful, but don't show your reasoning steps.

        STYLE:
        - Friendly, concise, confident.
        - Explain *why* a car or fuel type is a good fit.
        - Offer to compare options if user is confused.
        - If the answer depends on their needs (budget, city, usage, family size), ask 1–2 clarifying questions.
        - Never invent spinny processes or prices not present in context; speak in approximate ranges instead.

        OUTPUT FORMAT:
        - Short overview (2–3 sentences).
        - Then bullet points for key reasoning.
        - If relevant cars are provided, mention 2–5 good fits and why.
    """)

    # Build messages list like Perplexity: single turn + history
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)  # previous turns (user/assistant)

    user_content = f"""
    User question: {query}

    Relevant Spinny car data (sample rows, not exhaustive):
    {car_context}

    Please answer using the above data when relevant. 
    Do NOT show any chain-of-thought or step-by-step reasoning, 
    just the final explanation.
    """
    messages.append({"role": "user", "content": user_content})

    payload = {
        "model": "tngtech/deepseek-r1t2-chimera:free",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 800,
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"].strip()


# ------------- SIMPLE CAR RETRIEVAL -------------
def filter_cars(query: str, max_rows: int = 10) -> pd.DataFrame:
    """
    Very simple heuristic filter:
    - Look for city names, fuel type keywords, and budget numbers in the query.
    - Return a small subset to feed as context to the model.
    """

    df = cars_df.copy()

    q_lower = query.lower()

    # Fuel type heuristic
    fuel_map = {
        "petrol": "petrol",
        "diesel": "diesel",
        "cng": "cng",
        "hybrid": "hybrid",
        "electric": "electric",
        "ev": "electric",
    }
    for word, ft in fuel_map.items():
        if word in q_lower and "Fuel Type" in df.columns:
            df = df[df["Fuel Type"].str.lower().str.contains(ft, na=False)]
            break

    # Transmission heuristic
    if "automatic" in q_lower and "Transmission Type" in df.columns:
        df = df[df["Transmission Type"].str.lower().str.contains("auto", na=False)]
    elif "manual" in q_lower and "Transmission Type" in df.columns:
        df = df[df["Transmission Type"].str.lower().str.contains("man", na=False)]

    # Very rough budget detection like "8 lakh", "800000"
    import re
    budget_match = re.search(r"(\d+)\s*(lakh|lac|lk)", q_lower)
    if budget_match and "Procurement Price" in df.columns:
        lakhs = int(budget_match.group(1))
        rupees = lakhs * 100000
        df = df[df["Procurement Price"] <= rupees]

    # City heuristic
    if "City" in df.columns:
        for city in df["City"].dropna().unique():
            if str(city).lower() in q_lower:
                df = df[df["City"].str.lower() == str(city).lower()]
                break

    return df.head(max_rows)


def cars_to_context(df: pd.DataFrame) -> str:
    """
    Turn a small cars dataframe into a compact text table for the model.
    """
    if df.empty:
        return "No specific cars matched; you can answer more generally."

    cols = [c for c in df.columns if c in [
        "City", "Make", "Model", "Variant",
        "Make Year", "Fuel Type", "Transmission Type",
        "Mileage", "Ownership", "Procurement Price"
    ]]
    df_small = df[cols].copy()

    # Convert to a simple markdown-style table string
    lines = []
    header = " | ".join(cols)
    lines.append(header)
    lines.append("-" * len(header))
    for _, row in df_small.iterrows():
        vals = [str(row[c]) for c in cols]
        lines.append(" | ".join(vals))
    return "\n".join(lines)


# ------------- UI -------------
st.title("🚗 Spinny Mitra – Car Perplexity")

st.caption(
    "Ask anything about used cars – budget, city, fuel type, safety, comparison, EMI, etc. "
    "Spinny Mitra will answer like Perplexity, using Spinny-style car data as context."
)

# Left: chat; Right: car candidates
col_chat, col_cars = st.columns([2.2, 1.3])

with col_chat:
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []  # list of {role, content} (no system)

    # show previous conversation
    for msg in st.session_state.chat_history:
        if msg["role"] == "user":
            with st.chat_message("user"):
                st.markdown(msg["content"])
        else:
            with st.chat_message("assistant"):
                st.markdown(msg["content"])

    user_query = st.chat_input("Ask Spinny Mitra anything about cars...")

    if user_query:
        # add user message to state
        st.session_state.chat_history.append(
            {"role": "user", "content": user_query}
        )

        # retrieve cars & build context
        ctx_df = filter_cars(user_query, max_rows=12)
        ctx_text = cars_to_context(ctx_df)

        with st.chat_message("assistant"):
            with st.spinner("Thinking like Perplexity…"):
                try:
                    answer = ask_deepseek(
                        query=user_query,
                        history=st.session_state.chat_history[:-1],  # previous turns
                        car_context=ctx_text,
                    )
                except Exception as e:
                    answer = f"Sorry, I ran into an error talking to the model: `{e}`"

                st.markdown(answer)

        st.session_state.chat_history.append(
            {"role": "assistant", "content": answer}
        )

with col_cars:
    st.subheader("📊 Cars used as context")
    if "chat_history" and st.session_state.chat_history:
        last_user = next(
            (m for m in reversed(st.session_state.chat_history) if m["role"] == "user"),
            None,
        )
        if last_user:
            ctx_df = filter_cars(last_user["content"], max_rows=30)
            if ctx_df.empty:
                st.info("No specific matches found. Showing random sample.")
                st.dataframe(cars_df.sample(min(10, len(cars_df))))
            else:
                st.dataframe(ctx_df)
    else:
        st.info("Ask a question to see relevant cars here.")
