import streamlit as st
import pandas as pd
import json
from openai import OpenAI
import os

# --------------------- SETUP ---------------------
st.set_page_config(page_title="Spinny AI Car Advisor", page_icon="🚗")

# load OpenAI client using environment var
import openai
openai.api_key = os.getenv("OPENAI_API_KEY")

@st.cache_data
def load_cars():
    return pd.read_csv("cars.csv")

cars_df = load_cars()

# --------------------- SESSION STATE ---------------------
if "messages" not in st.session_state:
    st.session_state.messages = []
if "preferences" not in st.session_state:
    st.session_state.preferences = {}
if "stage" not in st.session_state:
    st.session_state.stage = "collecting"

# --------------------- PROMPT ---------------------
SYSTEM_PROMPT = """
You are Spinny's AI Car Consultant.

Your job:
1. Ask friendly questions to understand user's ideal car.
2. Extract structured fields from user messages:
   - budget_min (int)
   - budget_max (int)
   - city (string)
   - fuel_type (Petrol/Diesel/CNG/Electric/Any)
   - body_type (Hatchback/Sedan/SUV/MPV/Any)
   - seats_min (int)
3. Output a conversational reply.
4. At the END, output ONLY a JSON object as last line (no explanation).

If no new info found, output {} as JSON.
"""

# --------------------- LLM CALL ---------------------
def call_llm(conversation):
    response = client.chat.completions.create(
        model="meituan/longcat-flash-chat:free",
        messages=[{"role": "system", "content": SYSTEM_PROMPT}] + conversation,
        temperature=0.4,
    )
    return response.choices[0].message.content


def parse_json_from_message(content: str):
    lines = content.splitlines()
    last = lines[-1].strip()

    try:
        prefs = json.loads(last)
        chat_text = "\n".join(lines[:-1]).strip()
        return chat_text, prefs
    except:
        # no json found
        return content, {}


def merge_prefs(current, new):
    for k, v in new.items():
        if v not in ["", None]:
            current[k] = v
    return current


def enough_prefs(prefs):
    return "budget_max" in prefs and "city" in prefs


# --------------------- FILTER LOGIC ---------------------
def filter_cars(prefs, df):
    filtered = df.copy()

    if "budget_min" in prefs:
        filtered = filtered[filtered["price"] >= int(prefs["budget_min"])]

    if "budget_max" in prefs:
        filtered = filtered[filtered["price"] <= int(prefs["budget_max"])]

    if "city" in prefs:
        filtered = filtered[filtered["city"].str.contains(prefs["city"], case=False, na=False)]

    if "fuel_type" in prefs and prefs["fuel_type"].lower() != "any":
        filtered = filtered[filtered["fuel_type"].str.contains(prefs["fuel_type"], case=False)]

    if "body_type" in prefs and prefs["body_type"].lower() != "any":
        filtered = filtered[filtered["body_type"].str.contains(prefs["body_type"], case=False)]

    if "seats_min" in prefs:
        filtered = filtered[filtered["seats"] >= int(prefs["seats_min"])]

    return filtered


def pretty_car(row):
    return (
        f"**{row['make']} {row['model']} {row['year']}**\n"
        f"- Price: ₹{int(row['price']):,}\n"
        f"- Fuel: {row['fuel_type']} | Body: {row['body_type']}\n"
        f"- Seats: {row['seats']} | Km Driven: {row['km_driven']:,}\n"
        f"- City: {row['city']} | Hub: {row['hub_name']}"
    )


# --------------------- UI ---------------------
st.title("🚗 Spinny AI Car Advisor (Chat-Only MVP)")

# Display past chat
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# Chat input
if prompt := st.chat_input("Tell me what kind of car you want..."):

    st.session_state.messages.append({"role": "user", "content": prompt})

    # ---- If we are still collecting preferences ----
    if st.session_state.stage == "collecting":

        llm_output = call_llm(st.session_state.messages)
        visible, new_prefs = parse_json_from_message(llm_output)

        st.session_state.preferences = merge_prefs(st.session_state.preferences, new_prefs)

        # Show assistant message
        with st.chat_message("assistant"):
            st.markdown(visible)
        st.session_state.messages.append({"role": "assistant", "content": visible})

        # If enough prefs → Recommend cars
        if enough_prefs(st.session_state.preferences):
            st.session_state.stage = "recommended"

            matches = filter_cars(st.session_state.preferences, cars_df)

            with st.chat_message("assistant"):
                if len(matches) == 0:
                    st.markdown("I didn't find matches in your city — but I found options in other hubs:")

                    relaxed = dict(st.session_state.preferences)
                    relaxed.pop("city", None)
                    alt = filter_cars(relaxed, cars_df).head(5)

                    if len(alt) == 0:
                        st.markdown("Still nothing. Try increasing budget or changing body type.")
                    else:
                        for _, row in alt.iterrows():
                            st.markdown(pretty_car(row))
                else:
                    st.markdown("Here are the best matches for you:")
                    for _, row in matches.head(5).iterrows():
                        st.markdown(pretty_car(row))

    # ---- Already recommended, now just follow-up chat ----
    else:
        followup_prompt = [
            {"role": "system", "content": "You already recommended cars. Continue conversation helpfully."}
        ] + st.session_state.messages

        reply = call_llm(followup_prompt)

        with st.chat_message("assistant"):
            st.markdown(reply)

        st.session_state.messages.append({"role": "assistant", "content": reply})
