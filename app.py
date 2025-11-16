import os
import streamlit as st
from openai import OpenAI

# ---------------- CONFIG ----------------
st.set_page_config(page_title="AI Car Buying Consultant", page_icon="🚗")

# Load OpenRouter API key
API_KEY = st.secrets.get("OPENROUTER_API_KEY", None) or os.getenv("OPENROUTER_API_KEY")
if not API_KEY:
    st.error("❌ OPENROUTER_API_KEY not set. Add it to Streamlit secrets or env vars.")
    st.stop()

# Create OpenRouter client
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=API_KEY
)

SYSTEM_PROMPT = """
You are an expert Indian car buying consultant.

Your job:
- Deeply understand the user's needs and constraints.
- Ask smart, minimal questions to clarify:
  budget (₹), city, family size, daily running (km/day), highway vs city, fuel preference,
  body style preference, brand preference, must-have features.
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
- End with a clear recommendation.

Tone:
- Friendly, helpful, consultative.
- Explain reasoning in simple, human language.
"""

# ---------------- SESSION STATE ----------------
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Hi! 👋 I’m your AI car consultant. Tell me your budget, city, family size, and driving usage — I’ll help you pick the perfect car.",
        }
    ]

# ---------------- UI HEADER ----------------
st.title("🚗 AI Car Buying Consultant")
st.caption("Ask anything about car decisions & comparisons — I'll help like a personal expert.")

# ---------------- SHOW CHAT HISTORY ----------------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ---------------- RESET BUTTON ----------------
if st.button("🔁 Reset conversation"):
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Conversation reset 😊 Tell me your budget, city, and usage again.",
        }
    ]
    st.experimental_rerun()

# ---------------- LLM CALL FUNCTION ----------------
def call_llm(chat_messages):
    response = client.chat.completions.create(
        model="qwen/qwen3-235b-a22b:free",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            *chat_messages,
        ],
        temperature=0.5,
        extra_headers={
            "HTTP-Referer": "https://your-app-url",
            "X-Title": "Spinny AI Car Consultant"
        }
    )
    return response.choices[0].message.content

# ---------------- HANDLE USER INPUT ----------------
user_input = st.chat_input("Ask me about any car or your needs...")

if user_input:
    # Add user message
    st.session_state.messages.append({"role": "user", "content": user_input})

    # Display it
    with st.chat_message("user"):
        st.markdown(user_input)

    # AI response
    with st.chat_message("assistant"):
        with st.spinner("Analyzing your requirements..."):
            reply = call_llm(st.session_state.messages)
            st.markdown(reply)

    # Save AI response
    st.session_state.messages.append({"role": "assistant", "content": reply})
