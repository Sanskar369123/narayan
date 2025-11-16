import os
import streamlit as st
from openai import OpenAI

# ---------------- CONFIG ----------------
st.set_page_config(page_title="AI Car Buying Consultant", page_icon="🚗")

# Load API key
API_KEY = st.secrets.get("OPENAI_API_KEY", None) or os.getenv("OPENAI_API_KEY")
if not API_KEY:
    st.error("❌ OPENAI_API_KEY not set. Please set it as env var or in Streamlit secrets.")
    st.stop()

client = OpenAI(api_key=API_KEY)

SYSTEM_PROMPT = """
You are an expert Indian car buying consultant.

Your job:
- Deeply understand the user's needs and constraints.
- Ask smart, minimal questions to clarify:
  budget (₹), city, family size, daily running (km/day), highway vs city, fuel preference, body style preference, brand preference, must-have features.
- Then recommend 2–5 specific car models available in India (including older model years if relevant).

When recommending:
- Group cars by segment (e.g. "premium hatchback", "compact SUV", "sedan").
- For each recommended car, clearly list:
  - Pros (mileage, comfort, safety, performance, space, features, resale, maintenance)
  - Cons / trade-offs
- Always explain WHY a particular car suits the user's profile.

Comparison behavior:
- If user mentions 2–3 cars, compare them clearly:
  - Which is better for city/highway
  - Which has better mileage
  - Which has better safety/build
  - Which is more comfortable
  - Which has lower long-term cost
- End with a clear recommendation: which one you would pick for this user and why.

Tone:
- Friendly, consultative, like a knowledgeable salesperson who is honest.
- Avoid overloading with specs; connect features to their real-life impact.

Important:
- Assume the user is in India unless they specify otherwise.
- If information about a very new car is uncertain, say so and reason based on segment + brand trends.
"""

# ---------------- SESSION STATE ----------------
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Hi! 👋 I’m your AI car buying consultant. Tell me a bit about your budget, where you drive, and who’ll use the car — and I’ll help you shortlist and compare options.",
        }
    ]

# ---------------- UI HEADER ----------------
st.title("🚗 AI Car Buying Consultant")
st.caption("Ask anything about which car to buy, comparisons, pros/cons, and I’ll guide you like a personal consultant.")

# ---------------- SHOW CHAT HISTORY ----------------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Optional: reset button
if st.button("🔁 Reset conversation"):
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Conversation reset. 😊 Tell me again: what kind of car are you considering (budget, usage, city, family size, etc.)?",
        }
    ]
    st.experimental_rerun()

# ---------------- HANDLE USER INPUT ----------------
user_input = st.chat_input("Describe your situation or ask about specific cars...")

def call_llm(chat_messages):
    """Call the OpenAI chat completion API with full conversation."""
    response = client.chat.completions.create(
        model="qwen/qwen3-235b-a22b:free",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            *chat_messages,
        ],
        temperature=0.5,
    )
    return response.choices[0].message.content

if user_input:
    # 1. Add user message to state
    st.session_state.messages.append({"role": "user", "content": user_input})

    # 2. Show user message immediately
    with st.chat_message("user"):
        st.markdown(user_input)

    # 3. Call LLM with full history
    with st.chat_message("assistant"):
        with st.spinner("Thinking about the best cars for you..."):
            reply = call_llm(st.session_state.messages)
            st.markdown(reply)

    # 4. Save assistant reply
    st.session_state.messages.append({"role": "assistant", "content": reply})
