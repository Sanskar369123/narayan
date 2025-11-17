###############################################################
# SPINNY AI CAR CONSULTANT – PREMIUM CHATGPT UI (Option A)
###############################################################

import os
import re
import json
import requests
import streamlit as st

# ------------------------------------------------------------
# BASIC CONFIG
# ------------------------------------------------------------
st.set_page_config(
    page_title="Spinny AI Car Consultant",
    page_icon="🚗",
    layout="centered"
)

def show_followup(question_text=None, mode="guide"):
    """Always show a follow-up question above the chat input."""

    fallback_questions = {
        "guide": [
            "Would you like to compare these cars?",
            "Want me to suggest cheaper or premium alternatives?",
            "Should I shortlist the best value model for you?",
        ],
        "compare": [
            "Do you want me to compare variants?",
            "Would you like cheaper or premium alternatives?",
            "Should I check which one is better for long-term ownership?",
        ],
        "tips": [
            "Want more tips on test driving?",
            "Need help choosing between new vs used?",
            "Want me to suggest ideal segments for you?",
        ],
    }

    import random
    if not question_text:
        question_text = random.choice(fallback_questions.get(mode, fallback_questions["guide"]))

    with st.chat_message("assistant"):
        st.markdown(
            f"<div class='assistant-bubble'>{question_text}</div>",
            unsafe_allow_html=True
        )

API_KEY = st.secrets.get("OPENROUTER_API_KEY") or os.getenv("OPENROUTER_API_KEY")
if not API_KEY:
    st.error("❌ OPENROUTER_API_KEY missing")
    st.stop()

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# ------------------------------------------------------------
# PREMIUM UI
# ------------------------------------------------------------
st.markdown("""
<style>
    body, .main, .block-container { background-color: #F5F6F7 !important; }

    .block-container {
        max-width: 750px;
        margin: auto;
        padding-top: 20px;
    }

    .assistant-bubble {
        background: #FFFFFF;
        padding: 14px 18px;
        border-radius: 14px;
        border: 1px solid #E5E7EB;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        max-width: 80%;
        margin-bottom: 8px;
    }

    .user-bubble {
        background: #E11B22;
        color: white;
        padding: 14px 18px;
        border-radius: 14px;
        max-width: 80%;
        margin-left: auto;
        margin-bottom: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.15);
    }

    .car-card {
        background: white;
        border-radius: 16px;
        padding: 16px;
        border: 1px solid #E5E7EB;
        margin-bottom: 12px;
    }

    /* MAKE FOLLOWUP BAR VISIBLE & ALWAYS ABOVE INPUT */
    .followup-bar {
        background: #FFFFFF;
        padding: 10px;
        border-radius: 12px;
        border: 1px solid #E5E7EB;
        margin-top: 16px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.08);
    }

</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------
# SESSION STATE
# ------------------------------------------------------------
def init_state():
    defaults = {
        "mode": None,
        "stage": "init",
        "prefs": {},
        "messages": [],
        "reco_json": None,
        "raw_reco": "",
        "compare_json": None,
        "compare_raw": "",
        "pending_compare_query": None,
        "generated_tips": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# ------------------------------------------------------------
# PROMPTS
# ------------------------------------------------------------
CONSULTANT_PROMPT = """
You are an Indian car consultant. Based on conversation history, return:
{
 "cars":[
   {"name":"","segment":"","summary":"",
    "pros":[],"cons":[],"price_band":"","ideal_for":""}
 ],
 "cheaper_alternatives":[],
 "premium_alternatives":[],
 "followup_question":""
}
Return ONLY JSON.
"""

COMPARE_PROMPT = """
Compare the cars mentioned in conversation. Return ONLY JSON:
{
 "cars":[
   {"name":"","pros":[],"cons":[],"summary":""},
   {"name":"","pros":[],"cons":[],"summary":""}
 ],
 "winner":"",
 "reason":""
}
"""

TIPS_PROMPT = """
Give 6–10 bullet tips for buying a car based on conversation.
Return plain text bullets.
"""

# ------------------------------------------------------------
# CALL LLM
# ------------------------------------------------------------
def call_llm(messages):
    try:
        r = requests.post(
            OPENROUTER_URL,
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            data=json.dumps({
                "model": "tngtech/deepseek-r1t2-chimera:free",
                "messages": messages,
                "temperature": 0.2
            })
        )
        return r.json()["choices"][0]["message"]["content"]
    except:
        return None

def extract_json(text):
    if not text:
        return None
    try:
        return json.loads(text)
    except:
        pass
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except:
            return None
    return None

# ------------------------------------------------------------
# INITIAL MODE SELECTION
# ------------------------------------------------------------
if st.session_state.stage == "init":

    st.markdown("## 🚗 Spinny AI Car Consultant")
    st.markdown("#### How can I help you today?")

    mode = st.radio(
        "Choose:",
        ["Guide me to choose a car", "Compare models", "Car buying tips"],
        label_visibility="collapsed",
    )

    if st.button("Continue ➡️"):
        if "Guide" in mode:
            st.session_state.mode = "choose"
            st.session_state.stage = "q1"
        elif "Compare" in mode:
            st.session_state.mode = "compare"
            st.session_state.stage = "ask_compare"
        else:
            st.session_state.mode = "tips"
            st.session_state.stage = "tq1"
        st.rerun()
    st.stop()

# ------------------------------------------------------------
# SIDEBAR
# ------------------------------------------------------------
with st.sidebar:
    st.markdown("### Your Preferences")
    if st.session_state.prefs:
        for k, v in st.session_state.prefs.items():
            st.write(f"**{k.upper()}**: {v}")
    else:
        st.caption("As you answer, details appear here.")

    if st.button("Reset All"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

# ------------------------------------------------------------
# DISPLAY CHAT HISTORY
# ------------------------------------------------------------
for msg in st.session_state.messages:
    bubble_class = "assistant-bubble" if msg["role"] == "assistant" else "user-bubble"
    with st.chat_message(msg["role"]):
        st.markdown(f"<div class='{bubble_class}'>{msg['content']}</div>", unsafe_allow_html=True)

# ------------------------------------------------------------
# MODE: GUIDE ME TO CHOOSE A CAR
# ------------------------------------------------------------
if st.session_state.mode == "choose":

    QUESTIONS = {
        "q1": "Is this your first car?",
        "q2": "Who will drive the car mostly?",
        "q3": "What is your budget?",
        "q4": "Which city do you live in?",
        "q5": "How many people usually travel?",
        "q6": "How many km/day?",
        "q7": "Usage mostly: city/highway/mixed?",
        "q8": "Roads condition?",
        "q9": "Fuel type preference?",
        "q10": "Manual or automatic?",
        "q11": "Priority: mileage, safety, comfort, features?",
    }

    stage = st.session_state.stage

    if stage in QUESTIONS:
        q = QUESTIONS[stage]
        with st.chat_message("assistant"):
            st.markdown(f"<div class='assistant-bubble'>{q}</div>", unsafe_allow_html=True)

        ans = st.chat_input("Your answer...")
        if ans:
            st.session_state.prefs[stage] = ans
            st.session_state.messages.append({"role": "user", "content": ans})
            nextnum = int(stage[1:])
            st.session_state.stage = "reco" if nextnum == 11 else f"q{nextnum+1}"
            st.rerun()

    elif stage == "reco":
        with st.chat_message("assistant"):
            with st.spinner("Finding the perfect cars for you..."):
                raw = call_llm([{"role": "system", "content": CONSULTANT_PROMPT}] + st.session_state.messages)

        st.session_state.raw_reco = raw
        st.session_state.reco_json = extract_json(raw)
        st.session_state.stage = "show_reco"
        st.rerun()

    elif stage == "show_reco":
        data = st.session_state.reco_json or {}

        # car recommendations
        for car in data.get("cars", []):
            with st.chat_message("assistant"):
                st.markdown(
                    f"""
                    <div class='car-card'>
                        <h4>{car.get('name','')}</h4>
                        <p style='color:#777'>{car.get('segment','')}</p>
                        <p>{car.get('summary','')}</p>
                        <b>Pros:</b>
                        <ul>{''.join([f"<li>{p}</li>" for p in car.get('pros',[])])}</ul>
                        <b>Cons:</b>
                        <ul>{''.join([f"<li>{c}</li>" for c in car.get('cons',[])])}</ul>
                        <b>Ideal for:</b> {car.get('ideal_for','')}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        # Follow-up bar
        st.markdown("### 🔁 Continue the Conversation")
        st.markdown("<div class='followup-bar'>Ask more or refine:</div>", unsafe_allow_html=True)

        fu = st.chat_input("Type follow-up question...")
        if fu:
            st.session_state.messages.append({"role": "user", "content": fu})
            st.session_state.stage = "reco"
            st.rerun()

# ------------------------------------------------------------
# MODE: COMPARE CARS
# ------------------------------------------------------------
elif st.session_state.mode == "compare":

    if st.session_state.stage == "ask_compare":
        with st.chat_message("assistant"):
            st.markdown("<div class='assistant-bubble'>Which cars to compare? (e.g. Creta vs Seltos)</div>", unsafe_allow_html=True)

        inp = st.chat_input("Enter models...")
        if inp:
            st.session_state.messages.append({"role": "user", "content": inp})
            st.session_state.stage = "run_compare"
            st.rerun()

    elif st.session_state.stage == "run_compare":

        if st.session_state.pending_compare_query:
            st.session_state.messages.append({"role": "user", "content": st.session_state.pending_compare_query})
            st.session_state.pending_compare_query = None

        with st.chat_message("assistant"):
            with st.spinner("Comparing cars..."):
                raw = call_llm([{"role": "system", "content": COMPARE_PROMPT}] + st.session_state.messages)

        st.session_state.compare_raw = raw
        st.session_state.compare_json = extract_json(raw)
        st.session_state.stage = "show_compare"
        st.rerun()

    elif st.session_state.stage == "show_compare":
        data = st.session_state.compare_json or {}

        cars = data.get("cars", [])
        if len(cars) >= 2:
            c1, c2 = st.columns(2)
            left, right = cars[0], cars[1]

            with c1:
                st.markdown(
                    f"""
                    <div class='car-card'>
                        <h4>{left.get('name','')}</h4>
                        <b>Pros</b>
                        <ul>{''.join([f"<li>{p}</li>" for p in left.get('pros',[])])}</ul>
                        <b>Cons</b>
                        <ul>{''.join([f"<li>{c}</li>" for c in left.get('cons',[])])}</ul>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with c2:
                st.markdown(
                    f"""
                    <div class='car-card'>
                        <h4>{right.get('name','')}</h4>
                        <b>Pros</b>
                        <ul>{''.join([f"<li>{p}</li>" for p in right.get('pros',[])])}</ul>
                        <b>Cons</b>
                        <ul>{''.join([f"<li>{c}</li>" for c in right.get('cons',[])])}</ul>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        with st.chat_message("assistant"):
            st.markdown(
                f"<div class='assistant-bubble'>🏆 Winner: {data.get('winner','')}<br>{data.get('reason','')}</div>",
                unsafe_allow_html=True,
            )

        st.session_state.stage = "compare_followup"

    elif st.session_state.stage == "compare_followup":
        st.markdown("### 🔁 Continue Comparison")

        col1, col2 = st.columns(2)

        if col1.button("Compare variants"):
            st.session_state.pending_compare_query = "Compare variants of these cars."
            st.session_state.stage = "run_compare"
            st.rerun()

        if col1.button("Cheaper alternatives"):
            st.session_state.pending_compare_query = "Show cheaper alternatives."
            st.session_state.stage = "run_compare"
            st.rerun()

        if col2.button("Premium rivals"):
            st.session_state.pending_compare_query = "Show premium rivals."
            st.session_state.stage = "run_compare"
            st.rerun()

        if col2.button("Which is safer?"):
            st.session_state.pending_compare_query = "Which car is safer?"
            st.session_state.stage = "run_compare"
            st.rerun()

        usr = st.chat_input("Ask more about these cars...")
        if usr:
            st.session_state.pending_compare_query = usr
            st.session_state.stage = "run_compare"
            st.rerun()

# ------------------------------------------------------------
# MODE: TIPS
# ------------------------------------------------------------
elif st.session_state.mode == "tips":

    QUESTIONS = {
        "tq1": "Who are you buying the car for?",
        "tq2": "Your driving style (calm, fast, mixed)?",
        "tq3": "How many km/day?",
        "tq4": "Your priority: safety, mileage, comfort?",
    }

    stage = st.session_state.stage

    if stage in QUESTIONS:
        with st.chat_message("assistant"):
            st.markdown(f"<div class='assistant-bubble'>{QUESTIONS[stage]}</div>", unsafe_allow_html=True)

        ans = st.chat_input("Your answer...")
        if ans:
            st.session_state.messages.append({"role": "user", "content": ans})
            nextnum = int(stage[2:])
            st.session_state.stage = "run_tips" if nextnum == 4 else f"tq{nextnum+1}"
            st.rerun()

    elif stage == "run_tips":
        with st.chat_message("assistant"):
            with st.spinner("Preparing helpful tips..."):
                tips = call_llm([{"role": "system", "content": TIPS_PROMPT}] + st.session_state.messages)

        st.session_state.generated_tips = tips
        st.session_state.stage = "show_tips"
        st.rerun()

    elif stage == "show_tips":
        with st.chat_message("assistant"):
            st.markdown(
                f"<div class='assistant-bubble'>{st.session_state.generated_tips}</div>",
                unsafe_allow_html=True
            )
        st.session_state.stage = "tips_followup"

    elif stage == "tips_followup":
        st.markdown("### 🔁 Continue")

        col1, col2 = st.columns(2)

        if col1.button("How to test drive?"):
            st.session_state.messages.append({"role": "user", "content": "Give tips for test driving a car."})
            st.session_state.stage = "run_tips"
            st.rerun()

        if col1.button("New vs used?"):
            st.session_state.messages.append({"role": "user", "content": "Should I buy new or used?"})
            st.session_state.stage = "run_tips"
            st.rerun()

        if col2.button("Resale value?"):
            st.session_state.messages.append({"role": "user", "content": "Which cars have better resale value?"})
            st.session_state.stage = "run_tips"
            st.rerun()

        if col2.button("Maintenance tips"):
            st.session_state.messages.append({"role": "user", "content": "How to reduce maintenance cost?"})
            st.session_state.stage = "run_tips"
            st.rerun()

        usr = st.chat_input("Ask anything about buying a car...")
        if usr:
            st.session_state.messages.append({"role": "user", "content": usr})
            st.session_state.stage = "run_tips"
            st.rerun()

this code is working fine but this code doesnot allows for followup questions so i want that feature 
