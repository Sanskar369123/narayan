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
LIGHT_GREY = "#F7F7F7"

# ---------------- CSS ----------------
st.markdown("""
<style>

    /* GLOBAL LAYOUT CLEANUP */
    .block-container {
        max-width: 680px !important;
        margin: auto;
        padding-top: 2rem;
    }

    body, .main, .block-container {
        background-color: #F5F6F7 !important;
    }

    /* SIDEBAR */
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        border-right: 1px solid #EEE !important;
    }

    /* ASSISTANT BUBBLE */
    .assistant-bubble {
        background-color: #FFFFFF !important;
        border: 1px solid #E5E7EB !important;
        color: #111 !important;
        padding: 12px 16px;
        border-radius: 14px;
        margin-bottom: 10px;
        width: fit-content;
        max-width: 80%;
        box-shadow: 0px 1px 3px rgba(0,0,0,0.06);
    }

    /* USER BUBBLE */
    .user-bubble {
        background-color: #E11B22 !important;
        color: white !important;
        padding: 12px 16px;
        border-radius: 14px;
        margin-bottom: 10px;
        width: fit-content;
        max-width: 80%;
        margin-left: auto;
        box-shadow: 0px 1px 3px rgba(0,0,0,0.10);
    }

    /* CHAT INPUT BAR */
    div[data-testid="stChatInputContainer"] {
        background-color: #FFFFFF !important;
        padding: 10px 20px;
        border-top: 1px solid #EEE;
    }

    div[data-testid="stChatInputContainer"] textarea {
        background-color: #FFFFFF !important;
        color: #111 !important;
        border-radius: 16px !important;
        padding: 12px !important;
        border: 1px solid #DDD !important;
    }

    /* CLEAN UP DEFAULT STREAMLIT CROWDED SPACING */
    .css-1cpxqw2, .css-12oz5g7 { 
        padding-top: 0 !important;
    }

</style>
""", unsafe_allow_html=True)


# ---------------- SESSION ----------------
if "mode" not in st.session_state: st.session_state.mode = None
if "stage" not in st.session_state: st.session_state.stage = "init"
if "prefs" not in st.session_state: st.session_state.prefs = {}
if "messages" not in st.session_state: st.session_state.messages = []
if "followup_asked" not in st.session_state: st.session_state.followup_asked = False
if "last_recommendation" not in st.session_state: st.session_state.last_recommendation = ""

# ---------------- SYSTEM PROMPTS ----------------

CONSULTANT_PROMPT = """
You are an Indian car buying consultant. 
Use the user's context and preferences to recommend 2–4 cars.

Format your response in structured JSON with keys:
cars: list of car objects 
each car contains:
  - name
  - segment
  - summary
  - pros (list)
  - cons (list)
  - price_band
  - ideal_for

ALSO suggest:
  - cheaper_alternatives (list of names)
  - premium_alternatives (list of names)
  - followup_question (1 natural question)

Keep answers short, clean, and practical.
"""

COMPARE_PROMPT = """
You are an Indian car expert. Compare two cars thoroughly but briefly.
Format your output in JSON:

{
 "cars": [
   {
     "name": "...",
     "pros": ["..."],
     "cons": ["..."],
     "verdict": "short summary"
   },
   {... second car ...}
 ],
 "winner": "Car name",
 "reason": "why it's better for the user"
}
"""

TIPS_PROMPT = """
Generate short, personalised car buying tips based on user answers.
Return plain text suggestions in 6–8 bullet points.
"""


# ---------------- OPENROUTER ----------------
def call_llm(messages):
    payload = {
        "model": "tngtech/deepseek-r1t2-chimera:free",
        "messages": messages,
        "temperature": 0.3,
    }
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    r = requests.post(OPENROUTER_URL, headers=headers, data=json.dumps(payload))
    if r.status_code != 200:
        return None
    return r.json()["choices"][0]["message"]["content"]


# ---------------- FOLLOW-UP LOGIC ----------------
def smart_followup():
    prefs = st.session_state.prefs

    if "q11" in prefs and "safety" in prefs["q11"].lower():
        return "Since safety is your top priority, should I limit suggestions to 4–5 star rated cars?"

    if "q6" in prefs:
        km = "".join([d for d in prefs["q6"] if d.isdigit()])
        if km and int(km) > 30:
            return "Because you drive a lot daily, do you want me to show CNG or diesel options as well?"

    if "q5" in prefs:
        fam = "".join([d for d in prefs["q5"] if d.isdigit()])
        if fam and int(fam) >= 5:
            return "Would you like to explore 6–7 seater options too?"

    return "Would you like me to compare your top options or show alternatives?"


# ---------------- MODE SELECT SCREEN ----------------
if st.session_state.stage == "init":
    st.markdown("## 🚗 Spinny AI Car Advisor\nHow can I help you today?")
    mode = st.radio(
        "",
        ["Guide me to choose a car", "Compare models", "Car buying tips"]
    )
    if st.button("Continue ➡️"):
        if "Guide" in mode:
            st.session_state.mode = "choose"
            st.session_state.stage = "q1"
        elif "Compare" in mode:
            st.session_state.mode = "compare"
            st.session_state.stage = "ask_models"
        else:
            st.session_state.mode = "tips"
            st.session_state.stage = "tq1"
        st.rerun()
    st.stop()

# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.title("📝 Your Profile")
    if st.session_state.prefs:
        for k, v in st.session_state.prefs.items():
            st.write(f"**{k.upper()}**: {v}")
    if st.button("Reset"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()


# ---------------- CHAT RENDER ----------------
for msg in st.session_state.messages:
    bubble = "assistant-bubble" if msg["role"] == "assistant" else "user-bubble"
    with st.chat_message(msg["role"]):
        st.markdown(
            f"<div class='{bubble}'>{msg['content']}</div>",
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------
#  MODE: CAR SELECTION (GUIDED)
# ---------------------------------------------------------------------
if st.session_state.mode == "choose":

    QUESTIONS = {
        "q1": "Is this your first car?",
        "q2": "Who will drive it most of the time?",
        "q3": "What’s your budget? (e.g. 6–8 lakhs)",
        "q4": "Which city do you stay in?",
        "q5": "How many people usually travel?",
        "q6": "How many km do you drive in a day?",
        "q7": "Is your usage mostly city, highway, or mixed?",
        "q8": "Are your roads mostly smooth or rough?",
        "q9": "Any fuel preference?",
        "q10": "Manual or automatic?",
        "q11": "What's your priority? Mileage / Safety / Comfort / Features?",
    }

    # Ask Q&A
    if st.session_state.stage in QUESTIONS:
        question = QUESTIONS[st.session_state.stage]

        with st.chat_message("assistant"):
            st.markdown(f"<div class='chat-bubble assistant-bubble'>{question}</div>", unsafe_allow_html=True)

        user_input = st.chat_input("Your answer...")
        if user_input:
            st.session_state.messages.append({"role": "user", "content": user_input})
            st.session_state.prefs[st.session_state.stage] = user_input

            idx = int(st.session_state.stage[1:])
            st.session_state.stage = "recommend" if idx == 11 else f"q{idx + 1}"
            st.rerun()

    # Generate first recommendation
    elif st.session_state.stage == "recommend":
        with st.chat_message("assistant"):
            with st.spinner("Shortlisting the perfect cars for you..."):
                msgs = [{"role": "system", "content": CONSULTANT_PROMPT}] + st.session_state.messages
                raw = call_llm(msgs)

            st.session_state.last_recommendation = raw
            st.session_state.messages.append({"role": "assistant", "content": "Here are your best-fit cars 👇"})
            st.rerun()

    # Render recommendation in SPINNY CARD STYLE
    elif st.session_state.stage == "follow_up" or st.session_state.last_recommendation:
        try:
            data = json.loads(st.session_state.last_recommendation)
        except:
            st.error("Model returned invalid format.")
            st.stop()

        cars = data.get("cars", [])
        cheaper = data.get("cheaper_alternatives", [])
        premium = data.get("premium_alternatives", [])

        # Render each car as a SPINNY card
        for car in cars:
            with st.chat_message("assistant"):
                st.markdown(
                    f"""
                    <div style='background:white;padding:15px;border-radius:12px;border:1px solid #ddd;margin-bottom:12px;'>
                        <h4 style='margin:0;'>{car['name']} </h4>
                        <div style='color:#666;font-size:0.9rem;'>{car['segment']}</div>
                        <p style='margin-top:8px;font-size:0.9rem;'>{car['summary']}</p>
                        <b>Pros:</b>
                        <ul>{''.join([f"<li>{p}</li>" for p in car['pros']])}</ul>
                        <b>Cons:</b>
                        <ul>{''.join([f"<li>{c}</li>" for c in car['cons']])}</ul>
                        <b>Best for:</b> {car['ideal_for']}
                    </div>""",
                    unsafe_allow_html=True,
                )

        # Alternative Buttons
        with st.chat_message("assistant"):
            st.markdown("<div class='alt-buttons'>", unsafe_allow_html=True)

            if cheaper:
                if st.button("🔽 Show Cheaper Alternatives"):
                    user_q = "Show cheaper alternatives"
                    st.session_state.messages.append({"role": "user", "content": user_q})
                    st.session_state.stage = "alt-cheap"
                    st.rerun()

            if premium:
                if st.button("🔼 Show Premium Alternatives"):
                    user_q = "Show premium alternatives"
                    st.session_state.messages.append({"role": "user", "content": user_q})
                    st.session_state.stage = "alt-prem"
                    st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)

        # Ask follow-up once
        if not st.session_state.followup_asked:
            follow_q = data.get("followup_question") or smart_followup()
            st.session_state.messages.append({"role": "assistant", "content": follow_q})
            st.session_state.followup_asked = True
            st.rerun()

        user_follow_up = st.chat_input("Ask anything or answer the follow-up...")
        if user_follow_up:
            st.session_state.messages.append({"role": "user", "content": user_follow_up})
            st.session_state.stage = "recommend"  # regenerate refined recommendations
            st.rerun()


# ---------------------------------------------------------------------
#  MODE: ALTERNATIVES (Cheaper / Premium)
# ---------------------------------------------------------------------
if st.session_state.stage in ["alt-cheap", "alt-prem"]:
    with st.chat_message("assistant"):
        with st.spinner("Searching for alternatives..."):
            msgs = [{"role": "system", "content": CONSULTANT_PROMPT}] + st.session_state.messages
            alt_raw = call_llm(msgs)

    st.session_state.last_recommendation = alt_raw
    st.session_state.stage = "follow_up"
    st.rerun()


# ---------------------------------------------------------------------
#  MODE: COMPARISON (SIDE-BY-SIDE)
# ---------------------------------------------------------------------
if st.session_state.mode == "compare":

    if st.session_state.stage == "ask_models":
        with st.chat_message("assistant"):
            st.write("Which two car models do you want to compare?")
        user_input = st.chat_input("Example: Baleno vs i20")
        if user_input:
            st.session_state.messages.append({"role": "user", "content": user_input})
            st.session_state.stage = "run_compare"
            st.rerun()

    elif st.session_state.stage == "run_compare":
        with st.chat_message("assistant"):
            with st.spinner("Comparing both models..."):
                msgs = [{"role": "system", "content": COMPARE_PROMPT}] + st.session_state.messages
                raw = call_llm(msgs)

        try:
            data = json.loads(raw)
        except:
            st.error("Invalid JSON from model.")
            st.stop()

        cars = data["cars"]
        winner = data["winner"]

        # Render side-by-side cards
        c1, c2 = st.columns(2)
        for i, container in enumerate([c1, c2]):
            car = cars[i]
            with container:
                st.markdown("<div class='compare-card'>", unsafe_allow_html=True)
                st.markdown(
                    f"<div class='compare-title'>{car['name']}</div>",
                    unsafe_allow_html=True,
                )
                st.write("**Pros:**")
                for p in car["pros"]:
                    st.write(f"- {p}")
                st.write("**Cons:**")
                for c in car["cons"]:
                    st.write(f"- {c}")
                if car["name"] == winner:
                    st.markdown("<span class='badge-winner'>Winner</span>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

        # winner summary
        with st.chat_message("assistant"):
            st.write(f"🏆 **Winner:** {winner}")
            st.write(data["reason"])

        st.session_state.stage = "compare_followup"

    elif st.session_state.stage == "compare_followup":
        user_input = st.chat_input("Ask about another comparison or alternatives...")
        if user_input:
            st.session_state.messages.append({"role": "user", "content": user_input})
            st.session_state.stage = "run_compare"
            st.rerun()


# ---------------------------------------------------------------------
#  MODE: BUYING TIPS
# ---------------------------------------------------------------------
if st.session_state.mode == "tips":

    TIPS_Q = {
        "tq1": "Who are you buying the car for?",
        "tq2": "What’s the driving style?",
        "tq3": "How many km/day?",
        "tq4": "Your priorities?",
    }

    if st.session_state.stage in TIPS_Q:
        q = TIPS_Q[st.session_state.stage]
        with st.chat_message("assistant"):
            st.write(q)

        user_input = st.chat_input("Your answer...")
        if user_input:
            st.session_state.messages.append({"role": "user", "content": user_input})
            st.session_state.prefs[st.session_state.stage] = user_input
            idx = int(st.session_state.stage[2:])
            st.session_state.stage = "give_tips" if idx == 4 else f"tq{idx+1}"
            st.rerun()

    elif st.session_state.stage == "give_tips":
        with st.chat_message("assistant"):
            with st.spinner("Preparing tips for you..."):
                msgs = [{"role": "system", "content": TIPS_PROMPT}] + st.session_state.messages
                reply = call_llm(msgs)
            st.write(reply)

        st.session_state.stage = "tips_done"

    elif st.session_state.stage == "tips_done":
        user_input = st.chat_input("Any other doubts about buying a car?")
        if user_input:
            st.session_state.messages.append({"role": "user", "content": user_input})
            st.session_state.stage = "give_tips"
            st.rerun()
