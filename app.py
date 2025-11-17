###############################################################
# SPINNY AI CAR CONSULTANT – PREMIUM UI WITH UNIVERSAL FOLLOW-UPS
###############################################################

import os
import re
import json
import requests
import random
import streamlit as st

# ------------------------------------------------------------
# BASIC CONFIG
# ------------------------------------------------------------
st.set_page_config(
    page_title="Spinny AI Car Consultant",
    page_icon="🚗",
    layout="centered"
)

API_KEY = st.secrets.get("OPENROUTER_API_KEY") or os.getenv("OPENROUTER_API_KEY")
if not API_KEY:
    st.error("❌ OPENROUTER_API_KEY missing")
    st.stop()

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# ------------------------------------------------------------
# PREMIUM UI CSS
# ------------------------------------------------------------
st.markdown("""
<style>
    body, .main, .block-container { background-color: #F5F6F7 !important; }

    .block-container {
        max-width: 760px;
        padding-top: 20px;
    }

    .assistant-bubble {
        background: white;
        padding: 14px 18px;
        border-radius: 14px;
        border: 1px solid #E5E7EB;
        max-width: 80%;
        box-shadow: 0 1px 4px rgba(0,0,0,0.08);
        margin-bottom: 8px;
    }

    .user-bubble {
        background: #E11B22;
        color: white;
        padding: 14px 18px;
        border-radius: 14px;
        max-width: 80%;
        margin-left: auto;
        box-shadow: 0 1px 4px rgba(0,0,0,0.15);
        margin-bottom: 8px;
    }

    .car-card {
        background: white;
        border-radius: 14px;
        padding: 16px;
        border: 1px solid #E5E7EB;
        margin-bottom: 15px;
    }

    .followup-bar {
        margin-top: 18px;
        padding: 12px;
        background: white;
        border-radius: 14px;
        border: 1px solid #E5E7EB;
        box-shadow: 0 1px 4px rgba(0,0,0,0.08);
    }

</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------
# SESSION STATE
# ------------------------------------------------------------
def init_state():
    defaults = dict(
        mode=None,
        stage="init",
        prefs={},
        messages=[],
        reco_json=None,
        raw_reco="",
        compare_json=None,
        compare_raw="",
        pending_compare_query=None,
        generated_tips=None,
    )
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# ------------------------------------------------------------
# PROMPTS
# ------------------------------------------------------------
CONSULTANT_PROMPT = """
You are an Indian car consultant. Based on conversation history, return ONLY JSON:
{
 "cars":[
   {"name":"","segment":"","summary":"",
    "pros":[],"cons":[],"ideal_for":""}
 ],
 "cheaper_alternatives":[],
 "premium_alternatives":[],
 "followup_question":""
}
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
Give 6–10 practical bullet tips about buying a car based on the user's profile.
Return ONLY bullet points, plain text.
"""

# ------------------------------------------------------------
# LLM CALL
# ------------------------------------------------------------
def call_llm(messages):
    try:
        r = requests.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            },
            data=json.dumps({
                "model": "tngtech/deepseek-r1t2-chimera:free",
                "messages": messages,
                "temperature": 0.25,
            })
        )
        return r.json()["choices"][0]["message"]["content"]
    except:
        return ""

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
# UNIVERSAL FOLLOW-UP FUNCTION
# ------------------------------------------------------------
def show_followup(question_text=None, mode="guide"):
    """Shows a follow-up question ALWAYS above the input with fallback."""

    fallback = {
        "guide": [
            "Would you like me to compare these cars?",
            "Want cheaper or premium alternatives?",
            "Need help choosing the single best value car?",
        ],
        "compare": [
            "Want me to check variants?",
            "Should I compare cheaper or premium options?",
            "Want to know which is better for long-term use?",
        ],
        "tips": [
            "Want tips for a proper test drive?",
            "Should I help decide between new vs used?",
            "Want suggestions on ideal segments for you?",
        ]
    }

    if not question_text:
        question_text = random.choice(fallback.get(mode, fallback["guide"]))

    with st.chat_message("assistant"):
        st.markdown(f"<div class='assistant-bubble'>{question_text}</div>", unsafe_allow_html=True)

# ------------------------------------------------------------
# SIDEBAR
# ------------------------------------------------------------
with st.sidebar:
    st.markdown("### Your Profile")
    if st.session_state.prefs:
        for k, v in st.session_state.prefs.items():
            st.write(f"**{k.upper()}**: {v}")
    else:
        st.caption("Details appear as you answer.")

    if st.button("Reset"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

# ------------------------------------------------------------
# DISPLAY CHAT HISTORY
# ------------------------------------------------------------
for msg in st.session_state.messages:
    bubble = "assistant-bubble" if msg["role"] == "assistant" else "user-bubble"
    with st.chat_message(msg["role"]):
        st.markdown(f"<div class='{bubble}'>{msg['content']}</div>", unsafe_allow_html=True)

# ------------------------------------------------------------
# MODE: INITIAL SELECTION
# ------------------------------------------------------------
if st.session_state.stage == "init":

    st.markdown("## 🚗 Spinny AI Car Consultant")
    st.markdown("### How can I help you today?")

    mode = st.radio(
        "Choose:",
        ["Guide me to choose a car", "Compare models", "Car buying tips"],
        label_visibility="collapsed"
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
# MODE 1 : GUIDE ME TO CHOOSE A CAR
# ------------------------------------------------------------
if st.session_state.mode == "choose":

    QUESTIONS = {
        "q1": "Is this your first car?",
        "q2": "Who will drive the car mostly?",
        "q3": "What is your budget?",
        "q4": "Which city do you live in?",
        "q5": "How many people usually travel?",
        "q6": "How many km/day?",
        "q7": "Usage: city/highway/mixed?",
        "q8": "Road conditions?",
        "q9": "Fuel type preference?",
        "q10": "Manual or automatic?",
        "q11": "Priority: mileage/safety/features/comfort?",
    }

    # ------------------- QUESTION PHASE -------------------
    if st.session_state.stage in QUESTIONS:
        q = QUESTIONS[st.session_state.stage]

        with st.chat_message("assistant"):
            st.markdown(f"<div class='assistant-bubble'>{q}</div>", unsafe_allow_html=True)

        ans = st.chat_input("Your answer…")
        if ans:
            st.session_state.messages.append({"role": "user", "content": ans})
            st.session_state.prefs[st.session_state.stage] = ans

            nextq = int(st.session_state.stage[1:])
            st.session_state.stage = "reco" if nextq == 11 else f"q{nextq+1}"
            st.rerun()

    # ------------------- CALL MODEL -------------------
    elif st.session_state.stage == "reco":
        with st.chat_message("assistant"):
            with st.spinner("Finding the perfect cars…"):
                raw = call_llm([{"role": "system", "content": CONSULTANT_PROMPT}] + st.session_state.messages)

        st.session_state.raw_reco = raw
        st.session_state.reco_json = extract_json(raw)
        st.session_state.stage = "show_reco"
        st.rerun()

    # ------------------- SHOW RESULTS -------------------
    elif st.session_state.stage == "show_reco":
        data = st.session_state.reco_json or {}

        for car in data.get("cars", []):
            with st.chat_message("assistant"):
                st.markdown(
f"""
<div class='car-card'>
<h4>{car.get('name','')}</h4>
<p style='color:#666'>{car.get('segment','')}</p>
<p>{car.get('summary','')}</p>
<b>Pros:</b>
<ul>{''.join([f"<li>{p}</li>" for p in car.get('pros',[])])}</ul>
<b>Cons:</b>
<ul>{''.join([f"<li>{c}</li>" for c in car.get('cons',[])])}</ul>
<b>Ideal for:</b> {car.get('ideal_for','')}
</div>
""",
                    unsafe_allow_html=True)

        # 🔥 FOLLOW-UP APPEARS HERE
        followup = data.get("followup_question", None)
        show_followup(followup, "guide")

        # free chat
        fu = st.chat_input("Your follow-up…")
        if fu:
            st.session_state.messages.append({"role": "user", "content": fu})
            st.session_state.stage = "reco"
            st.rerun()

# ------------------------------------------------------------
# MODE 2 : COMPARE MODELS
# ------------------------------------------------------------
elif st.session_state.mode == "compare":

    if st.session_state.stage == "ask_compare":
        with st.chat_message("assistant"):
            st.markdown("<div class='assistant-bubble'>Which cars do you want to compare?</div>", unsafe_allow_html=True)

        text = st.chat_input("Example: Creta vs Seltos")
        if text:
            st.session_state.messages.append({"role": "user", "content": text})
            st.session_state.stage = "run_compare"
            st.rerun()

    elif st.session_state.stage == "run_compare":

        if st.session_state.pending_compare_query:
            st.session_state.messages.append({"role": "user", "content": st.session_state.pending_compare_query})
            st.session_state.pending_compare_query = None

        with st.chat_message("assistant"):
            with st.spinner("Comparing…"):
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
            L, R = cars[0], cars[1]

            with c1:
                st.markdown(f"""
                <div class='car-card'>
                <h4>{L.get('name','')}</h4>
                <b>Pros</b><ul>{''.join([f"<li>{p}</li>" for p in L.get('pros',[])])}</ul>
                <b>Cons</b><ul>{''.join([f"<li>{c}</li>" for c in L.get('cons',[])])}</ul>
                </div>
                """, unsafe_allow_html=True)
            with c2:
                st.markdown(f"""
                <div class='car-card'>
                <h4>{R.get('name','')}</h4>
                <b>Pros</b><ul>{''.join([f"<li>{p}</li>" for p in R.get('pros',[])])}</ul>
                <b>Cons</b><ul>{''.join([f"<li>{c}</li>" for c in R.get('cons',[])])}</ul>
                </div>
                """, unsafe_allow_html=True)

        with st.chat_message("assistant"):
            st.markdown(
                f"<div class='assistant-bubble'>🏆 Winner: {data.get('winner','')}<br>{data.get('reason','')}</div>",
                unsafe_allow_html=True
            )

        # 🔥 FOLLOW-UP QUESTION HERE
        show_followup(mode="compare")

        # user input follow-up
        usr = st.chat_input("Ask more…")
        if usr:
            st.session_state.pending_compare_query = usr
            st.session_state.stage = "run_compare"
            st.rerun()

# ------------------------------------------------------------
# MODE 3 : BUYING TIPS
# ------------------------------------------------------------
elif st.session_state.mode == "tips":

    QUESTIONS = {
        "tq1": "Who are you buying the car for?",
        "tq2": "Your driving style?",
        "tq3": "How many km/day?",
        "tq4": "Your top priority?",
    }

    stage = st.session_state.stage

    if stage in QUESTIONS:
        q = QUESTIONS[stage]
        with st.chat_message("assistant"):
            st.markdown(f"<div class='assistant-bubble'>{q}</div>", unsafe_allow_html=True)

        ans = st.chat_input("Your answer…")
        if ans:
            st.session_state.messages.append({"role": "user", "content": ans})
            nextq = int(stage[2:])
            st.session_state.stage = "run_tips" if nextq == 4 else f"tq{nextq+1}"
            st.rerun()

    elif stage == "run_tips":
        with st.chat_message("assistant"):
            with st.spinner("Preparing expert tips…"):
                tips = call_llm([{"role": "system", "content": TIPS_PROMPT}] + st.session_state.messages)
        st.session_state.generated_tips = tips
        st.session_state.stage = "show_tips"
        st.rerun()

    elif st.session_state.stage == "show_tips":
        with st.chat_message("assistant"):
            st.markdown(
                f"<div class='assistant-bubble'>{st.session_state.generated_tips}</div>",
                unsafe_allow_html=True
            )

        # 🔥 FOLLOW-UP QUESTION HERE
        show_followup(mode="tips")

        ask = st.chat_input("Ask more…")
        if ask:
            st.session_state.messages.append({"role": "user", "content": ask})
            st.session_state.stage = "run_tips"
            st.rerun()
