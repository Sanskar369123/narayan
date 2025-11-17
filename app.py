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

# ---------------- SYSTEM PROMPTS FOR EACH MODE ----------------

CONSULTANT_PROMPT = """
You are an Indian car buying consultant. Ask ONE QUESTION at a time.
Use simple language. Keep responses short.

You must collect:
1. First car or not
2. Primary driver
3. Budget
4. City
5. Family size
6. Daily running
7. Usage (City / Highway / Mixed)
8. Road quality
9. Fuel preference
10. Transmission
11. Priorities (mileage, safety, comfort, features)

After collecting all, recommend 2–4 cars with:
- segment
- one-line summary
- pros
- cons
- ideal user fit
"""

COMPARE_PROMPT = """
You are an expert car comparison specialist.
User will give 2–3 car model names.

Compare them on:
- Mileage
- Comfort
- Build quality
- Safety rating
- Features
- Ride quality
- Performance
- Maintenance cost
- Resale value
- Best for which type of user

End with: "Winner based on your needs: ___"
"""

TIPS_PROMPT = """
You are a helpful car buying advisor in India.
Ask the user 3–4 simple questions:
- Who are you buying for?
- Driving style?
- Running per day?
- Priorities?
Then give general car buying tips personalized to their answers.
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


# ---------------- FIRST SCREEN (MODE SELECTION) ----------------
if st.session_state.stage == "init":
    st.markdown("## 🚗 Spinny AI Car Advisor\nHow can I help you today?")
    choice = st.radio(
        "Choose an option:",
        ["Guide me to choose the perfect car", "Compare different car models", "Tips for buying a car"],
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
    for k, v in st.session_state.prefs.items():
        st.write(f"**{k.replace('_',' ').title()}**: {v}")

    if st.button("🔁 Reset"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()


# ---------------- CHAT DISPLAY ----------------
for msg in st.session_state.messages:
    role = msg["role"]
    bubble = "assistant-bubble" if role == "assistant" else "user-bubble"
    with st.chat_message(role):
        st.markdown(f"<div class='chat-bubble {bubble}'>{msg['content']}</div>", unsafe_allow_html=True)


# ---------------- MODE 1: GUIDED CAR SELECTION ----------------
if st.session_state.mode == "choose":

    QUESTIONS = {
        "q1": "Is this your first car or have you owned before?",
        "q2": "Who will drive the car most of the time?",
        "q3": "What's your budget range?",
        "q4": "Which city do you live in?",
        "q5": "How many family members usually travel?",
        "q6": "How many km do you drive per day?",
        "q7": "Is your driving mostly city, highway, or mixed?",
        "q8": "How are the roads? Mostly smooth or rough?",
        "q9": "Any fuel preference? Petrol / Diesel / CNG / Electric?",
        "q10": "Do you prefer manual or automatic?",
        "q11": "What matters most to you? Mileage / Safety / Comfort / Features / Low maintenance?",
    }

    # Determine if we are still asking questions
    if st.session_state.stage in QUESTIONS:
        q_text = QUESTIONS[st.session_state.stage]
        with st.chat_message("assistant"):
            st.markdown(f"<div class='chat-bubble assistant-bubble'>{q_text}</div>", unsafe_allow_html=True)
        user_input = st.chat_input("Your answer...")
        if user_input:
            # store answer
            st.session_state.prefs[st.session_state.stage] = user_input
            st.session_state.messages.append({"role": "user", "content": user_input})
            # next stage
            next_stage_num = int(st.session_state.stage[1:]) + 1
            st.session_state.stage = f"q{next_stage_num}"
            st.rerun()

    else:
        # Enough info → call LLM
        with st.chat_message("assistant"):
            with st.spinner("Analyzing your needs..."):
                msgs = [{"role": "system", "content": CONSULTANT_PROMPT}]
                for m in st.session_state.messages:
                    msgs.append(m)
                reply = call_llm(msgs)

            st.session_state.messages.append({"role": "assistant", "content": reply})
            st.markdown(f"<div class='chat-bubble assistant-bubble'>{reply}</div>", unsafe_allow_html=True)


# ---------------- MODE 2: CAR MODEL COMPARISON ----------------
if st.session_state.mode == "compare" and st.session_state.stage == "ask_models":
    with st.chat_message("assistant"):
        st.write("Which car models would you like to compare? (e.g., Baleno vs i20)")
    user_input = st.chat_input("Type models to compare...")
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        st.session_state.stage = "run_compare"
        st.rerun()

if st.session_state.mode == "compare" and st.session_state.stage == "run_compare":
    with st.chat_message("assistant"):
        with st.spinner("Comparing models..."):
            msgs = [{"role": "system", "content": COMPARE_PROMPT}] + st.session_state.messages
            reply = call_llm(msgs)
        st.session_state.messages.append({"role": "assistant", "content": reply})
        st.markdown(f"<div class='chat-bubble assistant-bubble'>{reply}</div>", unsafe_allow_html=True)


# ---------------- MODE 3: BUYING TIPS ----------------
if st.session_state.mode == "tips":

    TIPS_QUESTIONS = {
        "tq1": "Who are you buying the car for?",
        "tq2": "How would you describe your driving style?",
        "tq3": "How many km do you typically drive per day?",
        "tq4": "What are your top priorities? Mileage / Safety / Comfort / Features?",
    }

    if st.session_state.stage in TIPS_QUESTIONS:
        q = TIPS_QUESTIONS[st.session_state.stage]
        with st.chat_message("assistant"):
            st.write(q)
        user_input = st.chat_input("Your answer...")
        if user_input:
            st.session_state.prefs[st.session_state.stage] = user_input
            st.session_state.messages.append({"role": "user", "content": user_input})
            # move stage
            next_num = int(st.session_state.stage[2:]) + 1
            if next_num <= 4:
                st.session_state.stage = f"tq{next_num}"
            else:
                st.session_state.stage = "give_tips"
            st.rerun()

    elif st.session_state.stage == "give_tips":
        with st.chat_message("assistant"):
            with st.spinner("Preparing helpful tips for you..."):
                msgs = [{"role": "system", "content": TIPS_PROMPT}] + st.session_state.messages
                reply = call_llm(msgs)

        st.session_state.messages.append({"role": "assistant", "content": reply})
        st.markdown(f"<div class='chat-bubble assistant-bubble'>{reply}</div>", unsafe_allow_html=True)
