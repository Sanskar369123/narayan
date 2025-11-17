###############################################################
# SPINNY AI CAR CONSULTANT - FULL CLEAN VERSION
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

API_KEY = st.secrets.get("OPENROUTER_API_KEY") or os.getenv("OPENROUTER_API_KEY")
if not API_KEY:
    st.error("❌ Please set OPENROUTER_API_KEY in secrets/environment.")
    st.stop()

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# ------------------------------------------------------------
# CLEAN MINIMAL UI CSS
# ------------------------------------------------------------
st.markdown(
"""
<style>
    .block-container {
        max-width: 720px !important;
        margin: auto;
        padding-top: 2rem;
    }
    body, .main, .block-container {
        background-color: #F5F6F7 !important;
    }
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        border-right: 1px solid #EEE !important;
    }
    .assistant-bubble {
        background-color: #FFFFFF;
        border: 1px solid #E5E7EB;
        color: #111;
        padding: 12px 16px;
        border-radius: 14px;
        max-width: 80%;
        margin-bottom: 8px;
        box-shadow: 0px 1px 3px rgba(0,0,0,0.08);
    }
    .user-bubble {
        background-color: #E11B22;
        color: #FFF;
        padding: 12px 16px;
        border-radius: 14px;
        max-width: 80%;
        margin-left: auto;
        margin-bottom: 8px;
        box-shadow: 0px 1px 3px rgba(0,0,0,0.10);
    }
    div[data-testid="stChatInputContainer"] {
        background-color: #FFFFFF;
        border-top: 1px solid #EEE;
    }
    div[data-testid="stChatInputContainer"] textarea {
        border: 1px solid #DDD !important;
        border-radius: 14px !important;
        background-color: #FFFFFF !important;
        color: #111 !important;
    }
    .car-card {
        background-color: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 16px;
        padding: 14px;
        margin-bottom: 12px;
    }
</style>
""", unsafe_allow_html=True)


# ------------------------------------------------------------
# SESSION STATE
# ------------------------------------------------------------
if "mode" not in st.session_state:
    st.session_state.mode = None

if "stage" not in st.session_state:
    st.session_state.stage = "init"

if "prefs" not in st.session_state:
    st.session_state.prefs = {}

if "messages" not in st.session_state:
    st.session_state.messages = []

if "reco_json" not in st.session_state:
    st.session_state.reco_json = None

if "raw_reco" not in st.session_state:
    st.session_state.raw_reco = ""


# ------------------------------------------------------------
# PROMPTS
# ------------------------------------------------------------
CONSULTANT_PROMPT = """
You are an Indian car consultant. Based on conversation history, return:
{
 "cars":[
   {"name":"","segment":"","summary":"","pros":[],"cons":[],"price_band":"","ideal_for":""}
 ],
 "cheaper_alternatives":[],
 "premium_alternatives":[],
 "followup_question":""
}
Return ONLY JSON. No extra text.
"""

COMPARE_PROMPT = """
Given two cars to compare, return only JSON:
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
Based on the conversation, give 6–8 simple bullet tips.
Return plain text bullets (no JSON).
"""


# ------------------------------------------------------------
# UTILS
# ------------------------------------------------------------
def call_llm(messages):
    payload = {
        "model": "tngtech/deepseek-r1t2-chimera:free",
        "messages": messages,
        "temperature": 0.25
    }
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

    try:
        r = requests.post(OPENROUTER_URL, headers=headers, data=json.dumps(payload))
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
    try:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except:
        pass
    return None


# ------------------------------------------------------------
# MODE SELECTION
# ------------------------------------------------------------
if st.session_state.stage == "init":
    st.markdown("## 🚗 Spinny AI Car Consultant")
    st.markdown("#### How can I help you today?")

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
# SIDEBAR PROFILE
# ------------------------------------------------------------
with st.sidebar:
    st.markdown("### 👇 Your Preferences")
    if st.session_state.prefs:
        for k, v in st.session_state.prefs.items():
            st.write(f"**{k.upper()}**: {v}")
    else:
        st.caption("As you answer, details appear here.")
    if st.button("Reset"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()


# ------------------------------------------------------------
# RENDER CHAT HISTORY
# ------------------------------------------------------------
for m in st.session_state.messages:
    bubble = "assistant-bubble" if m["role"] == "assistant" else "user-bubble"
    with st.chat_message(m["role"]):
        st.markdown(f"<div class='{bubble}'>{m['content']}</div>", unsafe_allow_html=True)


# ============================================================
# MODE 1: GUIDE ME TO CHOOSE A CAR
# ============================================================
if st.session_state.mode == "choose":

    QUESTIONS = {
        "q1": "Is this your first car?",
        "q2": "Who will drive the car mostly?",
        "q3": "What is your budget? (e.g. ₹6–8 lakh)",
        "q4": "Which city do you live in?",
        "q5": "How many people travel usually?",
        "q6": "How many km/day do you drive?",
        "q7": "City, highway, or mixed usage?",
        "q8": "Roads: smooth or rough?",
        "q9": "Fuel preference (Petrol/Diesel/CNG/Electric)?",
        "q10": "Transmission (Manual/Automatic)?",
        "q11": "Top priority: mileage, safety, comfort, features, maintenance?",
    }

    # Ask questions one by one
    if st.session_state.stage in QUESTIONS:
        q = QUESTIONS[st.session_state.stage]
        with st.chat_message("assistant"):
            st.markdown(f"<div class='assistant-bubble'>{q}</div>", unsafe_allow_html=True)

        ans = st.chat_input("Your answer...")
        if ans:
            st.session_state.messages.append({"role": "user", "content": ans})
            st.session_state.prefs[st.session_state.stage] = ans
            i = int(st.session_state.stage[1:])
            st.session_state.stage = "reco" if i == 11 else f"q{i+1}"
            st.rerun()

    # Generate recommendation JSON
    elif st.session_state.stage == "reco":
        with st.chat_message("assistant"):
            with st.spinner("Finding best matches..."):
                msgs = [{"role": "system", "content": CONSULTANT_PROMPT}] + st.session_state.messages
                raw = call_llm(msgs)

        st.session_state.raw_reco = raw
        st.session_state.reco_json = extract_json(raw)
        st.session_state.stage = "show_reco"
        st.rerun()

    # Show recommendations
    elif st.session_state.stage == "show_reco":
        data = st.session_state.reco_json

        if data:
            cars = data.get("cars", [])
            cheaper = data.get("cheaper_alternatives", [])
            premium = data.get("premium_alternatives", [])
            follow_q = data.get("followup_question", "")

            for car in cars:
                with st.chat_message("assistant"):
                    st.markdown(
                        f"""
                        <div class='car-card'>
                            <h4>{car.get('name','')}</h4>
                            <p style='font-size:0.9rem;color:#555;'>{car.get('segment','')}</p>
                            <p>{car.get('summary','')}</p>

                            <b>Pros:</b>
                            <ul>{''.join([f"<li>{p}</li>" for p in car.get('pros',[])])}</ul>

                            <b>Cons:</b>
                            <ul>{''.join([f"<li>{c}</li>" for c in car.get('cons',[])])}</ul>

                            <b>Best for:</b> {car.get('ideal_for','')}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

            # Alternatives buttons
            with st.chat_message("assistant"):
                c1, c2 = st.columns(2)
                if cheaper:
                    if c1.button("🔽 Cheaper Alternatives"):
                        st.session_state.messages.append(
                            {"role": "user", "content": "Show cheaper alternatives."}
                        )
                        st.session_state.stage = "reco"
                        st.rerun()

                if premium:
                    if c2.button("🔼 Premium Options"):
                        st.session_state.messages.append(
                            {"role": "user", "content": "Show premium alternatives."}
                        )
                        st.session_state.stage = "reco"
                        st.rerun()

            # Follow-up question
            if follow_q:
                with st.chat_message("assistant"):
                    st.markdown(
                        f"<div class='assistant-bubble'>{follow_q}</div>", 
                        unsafe_allow_html=True
                    )

        else:
            # fallback
            with st.chat_message("assistant"):
                st.markdown(f"<div class='assistant-bubble'>{st.session_state.raw_reco}</div>", unsafe_allow_html=True)

        # Follow-up free chat
        inp = st.chat_input("Ask a follow-up...")
        if inp:
            st.session_state.messages.append({"role": "user", "content": inp})
            st.session_state.stage = "reco"
            st.rerun()


# ============================================================
# MODE 2: COMPARE MODELS (+ FOLLOW-UP)
# ============================================================
elif st.session_state.mode == "compare":

    if st.session_state.stage == "ask_compare":
        with st.chat_message("assistant"):
            st.markdown("<div class='assistant-bubble'>Which two models do you want to compare?</div>", unsafe_allow_html=True)

        inp = st.chat_input("e.g. Baleno vs i20")
        if inp:
            st.session_state.messages.append({"role": "user", "content": inp})
            st.session_state.stage = "run_compare"
            st.rerun()

    elif st.session_state.stage == "run_compare":
        with st.chat_message("assistant"):
            with st.spinner("Comparing models..."):
                msgs = [{"role": "system", "content": COMPARE_PROMPT}] + st.session_state.messages
                raw = call_llm(msgs)

        data = extract_json(raw)

        if data:
            cars = data.get("cars", [])
            winner = data.get("winner", "")
            reason = data.get("reason", "")

            if len(cars) >= 2:
                c1, c2 = st.columns(2)
                car1, car2 = cars[0], cars[1]

                with c1:
                    st.markdown(
                        f"""
                        <div class='car-card'>
                            <h4>{car1['name']}</h4>
                            <b>Pros:</b>
                            <ul>{''.join([f"<li>{p}</li>" for p in car1['pros']])}</ul>
                            <b>Cons:</b>
                            <ul>{''.join([f"<li>{c}</li>" for c in car1['cons']])}</ul>
                            <p><b>Summary:</b> {car1['summary']}</p>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                with c2:
                    st.markdown(
                        f"""
                        <div class='car-card'>
                            <h4>{car2['name']}</h4>
                            <b>Pros:</b>
                            <ul>{''.join([f"<li>{p}</li>" for p in car2['pros']])}</ul>
                            <b>Cons:</b>
                            <ul>{''.join([f"<li>{c}</li>" for c in car2['cons']])}</ul>
                            <p><b>Summary:</b> {car2['summary']}</p>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                with st.chat_message("assistant"):
                    st.markdown(
                        f"<div class='assistant-bubble'>🏆 <b>Winner:</b> {winner}<br>{reason}</div>",
                        unsafe_allow_html=True,
                    )

        else:
            with st.chat_message("assistant"):
                st.markdown(f"<div class='assistant-bubble'>{raw}</div>", unsafe_allow_html=True)

        st.session_state.stage = "compare_followup"
        st.rerun()

    elif st.session_state.stage == "compare_followup":
        with st.chat_message("assistant"):
            st.markdown(
                "<div class='assistant-bubble'>Want to explore more?</div>",
                unsafe_allow_html=True,
            )

        col1, col2 = st.columns(2)

        if col1.button("Compare variants"):
            st.session_state.messages.append({"role": "user", "content": "Compare the variants of both cars."})
            st.session_state.stage = "run_compare"
            st.rerun()

        if col1.button("Cheaper rivals"):
            st.session_state.messages.append({"role": "user", "content": "Show cheaper rivals."})
            st.session_state.stage = "run_compare"
            st.rerun()

        if col2.button("Premium rivals"):
            st.session_state.messages.append({"role": "user", "content": "Show premium competitions."})
            st.session_state.stage = "run_compare"
            st.rerun()

        if col2.button("Which is safer?"):
            st.session_state.messages.append({"role": "user", "content": "Which one is safer?"})
            st.session_state.stage = "run_compare"
            st.rerun()

        usr = st.chat_input("Ask a follow-up...")
        if usr:
            st.session_state.messages.append({"role": "user", "content": usr})
            st.session_state.stage = "run_compare"
            st.rerun()


# ============================================================
# MODE 3: BUYING TIPS (+ FOLLOW-UP)
# ============================================================
elif st.session_state.stage == "give_tips":

    # RUN LLM EXACTLY ONCE
    tips = st.session_state.get("generated_tips")

    if not tips:
        with st.chat_message("assistant"):
            with st.spinner("Preparing personalized tips..."):
                msgs = [{"role": "system", "content": TIPS_PROMPT}] + st.session_state.messages
                tips = call_llm(msgs)

        # SAVE RESULT (prevents re-running)
        st.session_state.generated_tips = tips

        # DISPLAY RESULT
        with st.chat_message("assistant"):
            st.markdown(f"<div class='assistant-bubble'>{tips}</div>", unsafe_allow_html=True)

        # move forward
        st.session_state.stage = "tips_followup"
        st.rerun()

    else:
        # If user returns here, show last tips
        with st.chat_message("assistant"):
            st.markdown(f"<div class='assistant-bubble'>{tips}</div>", unsafe_allow_html=True)

        st.session_state.stage = "tips_followup"
        st.rerun()


    elif st.session_state.stage == "give_tips":
        with st.chat_message("assistant"):
            with st.spinner("Preparing personalized tips..."):
                msgs = [{"role": "system", "content": TIPS_PROMPT}] + st.session_state.messages
                tips = call_llm(msgs)

            st.markdown(f"<div class='assistant-bubble'>{tips}</div>", unsafe_allow_html=True)

        st.session_state.stage = "tips_followup"
        st.rerun()

    elif st.session_state.stage == "tips_followup":
        with st.chat_message("assistant"):
            st.markdown("<div class='assistant-bubble'>Anything more I can help with?</div>", unsafe_allow_html=True)

        col1, col2 = st.columns(2)

        if col1.button("How to test drive?"):
            st.session_state.messages.append({"role": "user", "content": "Give me tips for test driving."})
            st.session_state.stage = "give_tips"
            st.rerun()

        if col1.button("New vs Used?"):
            st.session_state.messages.append({"role": "user", "content": "Should I buy new or used?"})
            st.session_state.stage = "give_tips"
            st.rerun()

        if col2.button("Resale value?"):
            st.session_state.messages.append({"role": "user", "content": "Which cars have better resale?"})
            st.session_state.stage = "give_tips"
            st.rerun()

        if col2.button("Maintenance tips"):
            st.session_state.messages.append({"role": "user", "content": "How to reduce maintenance cost?"})
            st.session_state.stage = "give_tips"
            st.rerun()

        ask = st.chat_input("Ask anything...")
        if ask:
            st.session_state.messages.append({"role": "user", "content": ask})
            st.session_state.stage = "give_tips"
            st.rerun()
