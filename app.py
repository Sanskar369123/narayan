import os
import json
import requests
import streamlit as st

# ---------------- CONFIG ----------------
st.set_page_config(
    page_title="AI Car Consultant • Spinny Style",
    page_icon="🚗",
    layout="centered"
)

API_KEY = st.secrets.get("OPENROUTER_API_KEY") or os.getenv("OPENROUTER_API_KEY")
if not API_KEY:
    st.error("❌ Please set OPENROUTER_API_KEY in secrets or env.")
    st.stop()

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

SPINNY_RED = "#E11B22"
LIGHT_GREY = "#F5F5F5"

# ---------------- CUSTOM CSS ----------------
st.markdown(
    f"""
    <style>
        body {{ background-color: {LIGHT_GREY}; }}
        .block-container {{
            max-width: 780px !important;
            padding-top: 1.5rem;
            padding-bottom: 4rem;
        }}
        .chat-bubble {{
            padding: 0.75rem 1rem;
            border-radius: 16px;
            margin-bottom: 0.5rem;
            max-width: 90%;
            font-size: 0.95rem;
            line-height: 1.4;
        }}
        .assistant-bubble {{
            background-color: #fff;
            border: 1px solid #e5e7eb;
            color: #111;
        }}
        .user-bubble {{
            background-color: {SPINNY_RED};
            color: white;
            margin-left: auto;
        }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------- SESSION STATE ----------------
if "mode" not in st.session_state:
    st.session_state.mode = None          # choose / compare / tips
if "stage" not in st.session_state:
    st.session_state.stage = "init"
if "prefs" not in st.session_state:
    st.session_state.prefs = {}
if "messages" not in st.session_state:
    st.session_state.messages = []
if "followup_asked" not in st.session_state:
    st.session_state.followup_asked = False

# ---------------- SYSTEM PROMPTS ----------------

# For guided car selection + follow-ups
CONSULTANT_PROMPT = """
You are an Indian car buying consultant.

The app has already collected these details from the user:
- First car or not
- Primary driver
- Budget
- City
- Family size
- Daily running
- Usage (city / highway / mixed)
- Road quality
- Fuel preference
- Transmission
- Priorities (mileage, safety, comfort, features, low maintenance, performance)

Your job:
1. Use these details to recommend 2–4 specific car models available in India.
2. For each car, clearly show:
   - Segment (e.g., premium hatchback, compact SUV)
   - One-line summary
   - Pros (bullet points)
   - Cons (bullet points)
   - Who this car is best for (1 line)
3. Tie your reasoning back to the user's profile ("Since you drive 40 km/day in city traffic and prefer comfort + automatic...").

If the user asks follow-up questions, refine or adjust recommendations, compare options, or suggest alternatives. 
Keep answers concise, friendly, and practical.
"""

# For comparison mode
COMPARE_PROMPT = """
You are an expert car comparison specialist in India.

User will give 2–3 car model names.

Compare them on:
- Mileage
- Comfort
- Build quality
- Safety
- Features
- Ride quality
- Performance
- Maintenance cost
- Resale value

End with: "Winner based on your needs: ___" and explain why.
Keep it short and readable.
"""

# For tips mode
TIPS_PROMPT = """
You are a helpful Indian car buying advisor.

The app collects a few details:
- Who they are buying for
- Driving style
- Daily running
- Priorities (mileage / safety / comfort / features)

Based on that, give 5–8 practical tips on:
- How to shortlist the right segment
- What to test during a test drive
- Common mistakes to avoid
- Fuel / transmission choices
- Safety and budget balance

Keep tone friendly and simple.
"""


# ---------------- OPENROUTER CALL ----------------
def call_llm(messages):
    payload = {
        "model": "tngtech/deepseek-r1t2-chimera:free",
        "messages": messages,
        "temperature": 0.25,
    }

    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    response = requests.post(OPENROUTER_URL, headers=headers, data=json.dumps(payload))

    if response.status_code != 200:
        return "⚠️ Error from LLM: " + response.text

    return response.json()["choices"][0]["message"]["content"]


# ---------------- FOLLOW-UP QUESTION ENGINE (for choose mode) ----------------
def get_followup_question():
    prefs = st.session_state.prefs

    # Budget-based follow-up
    if "q3" in prefs and "lakh" in prefs["q3"].lower():
        return "Would you like to explore a bit above or below your budget to see better value options?"

    # Safety-focused
    if "q11" in prefs and "safety" in prefs["q11"].lower():
        return "Since safety is important to you, should I focus only on cars with strong safety ratings (like 4–5 star NCAP)?"

    # High daily running
    if "q6" in prefs:
        try:
            daily_km = int("".join(filter(str.isdigit, prefs["q6"])))
            if daily_km > 30:
                return "Since your daily running is high, do you want to explore CNG or diesel options as well to save on running costs?"
        except Exception:
            pass

    # Family size
    if "q5" in prefs:
        try:
            fam = int("".join(filter(str.isdigit, prefs["q5"])))
            if fam >= 5:
                return "Would you like me to include 6–7 seater options (like MPVs or bigger SUVs) in your shortlist?"
        except Exception:
            pass

    # City-specific traffic
    if "q4" in prefs:
        city = prefs["q4"].lower()
        if any(c in city for c in ["bangalore", "bengaluru", "mumbai", "delhi", "pune", "hyderabad"]):
            return "Since traffic is usually heavy in your city, would you prefer I prioritise automatic options for convenience?"

    # Bad roads
    if "q8" in prefs and any(w in prefs["q8"].lower() for w in ["bad", "broken", "potholes", "speed breaker"]):
        return "As your roads aren't great, should I focus on cars with good ground clearance and suspension?"

    # Default fallback
    return "Would you like me to compare your top 2 options in detail, or suggest a few alternatives in the same budget?"


# ---------------- FIRST SCREEN (MODE SELECTION) ----------------
if st.session_state.stage == "init":
    st.markdown("## 🚗 Spinny AI Car Advisor\nHow can I help you today?")
    choice = st.radio(
        "Choose an option:",
        [
            "Guide me to choose the perfect car",
            "Compare different car models",
            "Tips for buying a car",
        ],
    )

    if st.button("Continue ➡️"):
        if choice.startswith("Guide"):
            st.session_state.mode = "choose"
            st.session_state.stage = "q1"
        elif choice.startswith("Compare"):
            st.session_state.mode = "compare"
            st.session_state.stage = "ask_models"
        else:
            st.session_state.mode = "tips"
            st.session_state.stage = "tq1"
        st.rerun()

    st.stop()


# ---------------- SIDEBAR: USER PROFILE ----------------
with st.sidebar:
    st.markdown("### 🧾 Your Answers")
    if st.session_state.prefs:
        for k, v in st.session_state.prefs.items():
            label = k.replace("_", " ").upper()
            st.write(f"**{label}**: {v}")
    else:
        st.caption("Start answering and I’ll build your profile here. 🙂")

    if st.button("🔁 Reset"):
        # clear everything
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()


# ---------------- CHAT HISTORY RENDER ----------------
for msg in st.session_state.messages:
    role = msg["role"]
    bubble = "assistant-bubble" if role == "assistant" else "user-bubble"
    with st.chat_message(role):
        st.markdown(
            f"<div class='chat-bubble {bubble}'>{msg['content']}</div>",
            unsafe_allow_html=True,
        )


# ---------------- MODE 1: GUIDED CAR SELECTION ----------------
if st.session_state.mode == "choose":

    QUESTIONS = {
        "q1": "Is this your first car or have you owned one before?",
        "q2": "Who will drive the car most of the time — you, a family member, or a chauffeur?",
        "q3": "What's your budget range? (e.g., 6–8 lakhs, 10–12 lakhs)",
        "q4": "Which city do you live in or where will you mainly use the car?",
        "q5": "How many family members usually travel in the car?",
        "q6": "On average, how many kilometers do you drive per day?",
        "q7": "Is your usage mostly city, mostly highway, or a mix of both?",
        "q8": "How are the typical roads — mostly smooth, or a lot of bad roads and speed breakers?",
        "q9": "Do you have a fuel preference (Petrol / Diesel / CNG / Electric), or are you open to suggestions?",
        "q10": "Do you prefer manual or automatic transmission?",
        "q11": "What matters most to you? (Mileage / Safety / Comfort / Features / Low maintenance / Performance)",
    }

    # STAGE: asking fixed questions
    if st.session_state.stage in QUESTIONS:
        q_text = QUESTIONS[st.session_state.stage]

        # Show current question as assistant bubble (but don't duplicate in messages)
        with st.chat_message("assistant"):
            st.markdown(
                f"<div class='chat-bubble assistant-bubble'>{q_text}</div>",
                unsafe_allow_html=True,
            )

        user_input = st.chat_input("Your answer...")
        if user_input:
            # Save answer in prefs
            st.session_state.prefs[st.session_state.stage] = user_input
            # Add user message to history
            st.session_state.messages.append({"role": "user", "content": user_input})

            # Move to next stage
            current_idx = int(st.session_state.stage[1:])
            if current_idx >= len(QUESTIONS):
                st.session_state.stage = "recommend"
            else:
                st.session_state.stage = f"q{current_idx + 1}"

            st.rerun()

    # STAGE: initial recommendation
    elif st.session_state.stage == "recommend":
        with st.chat_message("assistant"):
            with st.spinner("Analyzing your needs and shortlisting cars..."):
                msgs = [{"role": "system", "content": CONSULTANT_PROMPT}] + st.session_state.messages
                reply = call_llm(msgs)

            st.session_state.messages.append({"role": "assistant", "content": reply})
            st.markdown(
                f"<div class='chat-bubble assistant-bubble'>{reply}</div>",
                unsafe_allow_html=True,
            )

        # After first recommendation, go into follow-up mode
        st.session_state.stage = "follow_up"
        st.session_state.followup_asked = False
        st.rerun()

    # STAGE: follow-up logic
    elif st.session_state.stage == "follow_up":
        # If we haven't asked a follow-up yet, generate one and show it once
        if not st.session_state.followup_asked:
            follow_q = get_followup_question()
            st.session_state.messages.append({"role": "assistant", "content": follow_q})
            st.session_state.followup_asked = True
            st.rerun()
        else:
            # Show the chat (including follow-up question already stored), then take user input
            user_input = st.chat_input("Ask a question or answer the follow-up...")
            if user_input:
                st.session_state.messages.append({"role": "user", "content": user_input})

                with st.chat_message("assistant"):
                    with st.spinner("Refining suggestions for you..."):
                        msgs = [{"role": "system", "content": CONSULTANT_PROMPT}] + st.session_state.messages
                        reply = call_llm(msgs)
                    st.session_state.messages.append({"role": "assistant", "content": reply})
                    st.markdown(
                        f"<div class='chat-bubble assistant-bubble'>{reply}</div>",
                        unsafe_allow_html=True,
                    )

                # Stay in follow-up mode for more conversation
                st.rerun()


# ---------------- MODE 2: CAR MODEL COMPARISON ----------------
if st.session_state.mode == "compare":

    if st.session_state.stage == "ask_models":
        with st.chat_message("assistant"):
            st.markdown(
                "<div class='chat-bubble assistant-bubble'>Which car models would you like to compare? (e.g., Baleno vs i20)</div>",
                unsafe_allow_html=True,
            )
        user_input = st.chat_input("Type models to compare...")
        if user_input:
            st.session_state.messages.append({"role": "user", "content": user_input})
            st.session_state.stage = "run_compare"
            st.rerun()

    elif st.session_state.stage == "run_compare":
        with st.chat_message("assistant"):
            with st.spinner("Comparing models for you..."):
                msgs = [{"role": "system", "content": COMPARE_PROMPT}] + st.session_state.messages
                reply = call_llm(msgs)
            st.session_state.messages.append({"role": "assistant", "content": reply})
            st.markdown(
                f"<div class='chat-bubble assistant-bubble'>{reply}</div>",
                unsafe_allow_html=True,
            )

        # Mark comparison done
        st.session_state.stage = "compare_done"

    elif st.session_state.stage == "compare_done":
        # Free-form follow-up Q&A in compare context
        user_input = st.chat_input("Ask more about these models or another comparison...")
        if user_input:
            st.session_state.messages.append({"role": "user", "content": user_input})
            with st.chat_message("assistant"):
                with st.spinner("Let me help you with that..."):
                    msgs = [{"role": "system", "content": COMPARE_PROMPT}] + st.session_state.messages
                    reply = call_llm(msgs)
                st.session_state.messages.append({"role": "assistant", "content": reply})
                st.markdown(
                    f"<div class='chat-bubble assistant-bubble'>{reply}</div>",
                    unsafe_allow_html=True,
                )
            st.rerun()


# ---------------- MODE 3: BUYING TIPS ----------------
if st.session_state.mode == "tips":

    TIPS_QUESTIONS = {
        "tq1": "Who are you buying the car for? (e.g., yourself, parents, family, spouse)",
        "tq2": "How would you describe the driving style? (calm, spirited, mixed)",
        "tq3": "How many km do you typically drive per day?",
        "tq4": "What are your top priorities? (mileage, safety, comfort, features, low maintenance)",
    }

    if st.session_state.stage in TIPS_QUESTIONS:
        q = TIPS_QUESTIONS[st.session_state.stage]
        with st.chat_message("assistant"):
            st.markdown(f"<div class='chat-bubble assistant-bubble'>{q}</div>", unsafe_allow_html=True)

        user_input = st.chat_input("Your answer...")
        if user_input:
            st.session_state.prefs[st.session_state.stage] = user_input
            st.session_state.messages.append({"role": "user", "content": user_input})

            current_idx = int(st.session_state.stage[2:])
            if current_idx >= len(TIPS_QUESTIONS):
                st.session_state.stage = "give_tips"
            else:
                st.session_state.stage = f"tq{current_idx + 1}"
            st.rerun()

    elif st.session_state.stage == "give_tips":
        with st.chat_message("assistant"):
            with st.spinner("Preparing some useful tips for you..."):
                msgs = [{"role": "system", "content": TIPS_PROMPT}] + st.session_state.messages
                reply = call_llm(msgs)
            st.session_state.messages.append({"role": "assistant", "content": reply})
            st.markdown(
                f"<div class='chat-bubble assistant-bubble'>{reply}</div>",
                unsafe_allow_html=True,
            )
        st.session_state.stage = "tips_done"

    elif st.session_state.stage == "tips_done":
        user_input = st.chat_input("Any follow-up questions about buying a car?")
        if user_input:
            st.session_state.messages.append({"role": "user", "content": user_input})
            with st.chat_message("assistant"):
                with st.spinner("Let me help with that..."):
                    msgs = [{"role": "system", "content": TIPS_PROMPT}] + st.session_state.messages
                    reply = call_llm(msgs)
                st.session_state.messages.append({"role": "assistant", "content": reply})
                st.markdown(
                    f"<div class='chat-bubble assistant-bubble'>{reply}</div>",
                    unsafe_allow_html=True,
                )
            st.rerun()
