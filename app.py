import os
import re
import json
import requests
import streamlit as st

# -------------------------------------------------------------------
# BASIC CONFIG
# -------------------------------------------------------------------
st.set_page_config(
    page_title="Spinny AI Car Consultant",
    page_icon="🚗",
    layout="centered"
)

API_KEY = st.secrets.get("OPENROUTER_API_KEY") or os.getenv("OPENROUTER_API_KEY")
if not API_KEY:
    st.error("❌ Please set OPENROUTER_API_KEY in Streamlit secrets or environment.")
    st.stop()

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# -------------------------------------------------------------------
# SIMPLE, CLEAN CSS
# -------------------------------------------------------------------
st.markdown(
    """
    <style>
        .block-container {
            max-width: 720px !important;
            margin: auto;
            padding-top: 1.5rem;
            padding-bottom: 3rem;
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
            padding: 10px 14px;
            border-radius: 14px;
            margin-bottom: 8px;
            width: fit-content;
            max-width: 80%;
            box-shadow: 0px 1px 3px rgba(0,0,0,0.06);
        }
        .user-bubble {
            background-color: #E11B22;
            color: #FFFFFF;
            padding: 10px 14px;
            border-radius: 14px;
            margin-bottom: 8px;
            width: fit-content;
            max-width: 80%;
            margin-left: auto;
            box-shadow: 0px 1px 3px rgba(0,0,0,0.1);
        }
        div[data-testid="stChatInputContainer"] {
            background-color: #FFFFFF !important;
            border-top: 1px solid #EEE;
        }
        div[data-testid="stChatInputContainer"] textarea {
            border-radius: 16px !important;
            border: 1px solid #DDD !important;
            background-color: #FFFFFF !important;
            color: #111 !important;
            padding: 10px !important;
        }
        .car-card {
            background-color: #FFFFFF;
            border: 1px solid #E5E7EB;
            border-radius: 14px;
            padding: 12px 14px;
            margin-bottom: 10px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------------------------------------------------------
# SESSION STATE
# -------------------------------------------------------------------
if "mode" not in st.session_state:
    st.session_state.mode = None          # "choose" | "compare" | "tips"
if "stage" not in st.session_state:
    st.session_state.stage = "init"       # init, q1..q11, reco, show_reco, ...
if "prefs" not in st.session_state:
    st.session_state.prefs = {}
if "messages" not in st.session_state:
    st.session_state.messages = []        # list of {"role": "user"/"assistant", "content": str}
if "reco_json" not in st.session_state:
    st.session_state.reco_json = None     # parsed JSON for recommendations (if available)
if "raw_reco" not in st.session_state:
    st.session_state.raw_reco = ""        # raw text from LLM for reco (for fallback)

# -------------------------------------------------------------------
# PROMPTS
# -------------------------------------------------------------------
CONSULTANT_PROMPT = """
You are an Indian car buying consultant.

The conversation so far describes the user's situation:
- First car or not
- Who drives
- Budget
- City
- Family size
- Daily running
- Usage type (city/highway/mixed)
- Road quality
- Fuel preference
- Transmission
- Priority (mileage, safety, comfort, features, maintenance, performance)

Now:
1. Recommend 2–4 specific car models available in India that best fit.
2. For each car, provide:
   - name
   - segment
   - summary
   - pros (list)
   - cons (list)
   - price_band (string, e.g. "₹7–9L on-road")
   - ideal_for (short description)

3. Additionally provide:
   - cheaper_alternatives: list of model names (strings)
   - premium_alternatives: list of model names (strings)
   - followup_question: one friendly question to keep the conversation going

Return ONLY a JSON object with keys:
{
  "cars": [...],
  "cheaper_alternatives": [...],
  "premium_alternatives": [...],
  "followup_question": "..."
}
No extra text, no explanation outside JSON.
"""

COMPARE_PROMPT = """
You are an Indian car expert. The user will mention 2 car models to compare.

Return ONLY a JSON object:
{
  "cars": [
    {
      "name": "...",
      "pros": ["..."],
      "cons": ["..."],
      "summary": "short verdict for this car"
    },
    {
      "name": "...",
      "pros": ["..."],
      "cons": ["..."],
      "summary": "short verdict for this car"
    }
  ],
  "winner": "Name of winning car",
  "reason": "Why this car is better for this user"
}
Do not add any other text. No markdown. Only JSON.
"""

TIPS_PROMPT = """
You are a friendly car buying advisor in India.

Based on the conversation (for whom, driving style, daily running, priorities),
give 6–8 short, practical bullet-point tips to help the user choose a car,
test drive, and avoid common mistakes.

Return plain text (no JSON), with bullet points.
"""

# -------------------------------------------------------------------
# UTILS
# -------------------------------------------------------------------
def call_llm(messages):
    """Call OpenRouter chat completions using Deepseek Chimera."""
    payload = {
        "model": "tngtech/deepseek-r1t2-chimera:free",
        "messages": messages,
        "temperature": 0.25,
    }
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    resp = requests.post(OPENROUTER_URL, headers=headers, data=json.dumps(payload))
    if resp.status_code != 200:
        return None
    try:
        return resp.json()["choices"][0]["message"]["content"]
    except Exception:
        return None


def extract_json(text):
    """Robustly extract the first JSON object from a text."""
    if not text:
        return None
    try:
        # Try direct first
        return json.loads(text)
    except Exception:
        pass
    try:
        # Fallback: find {...} region
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except Exception:
        return None
    return None


# -------------------------------------------------------------------
# MODE SELECTION
# -------------------------------------------------------------------
if st.session_state.stage == "init":
    st.markdown("## 🚗 Spinny AI Car Advisor")
    st.markdown("#### How can I help you today?")

    mode = st.radio(
        "Choose an option",
        ["Guide me to choose a car", "Compare models", "Car buying tips"],
        label_visibility="collapsed",
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

# -------------------------------------------------------------------
# SIDEBAR: simple profile dump
# -------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 🧾 Your Profile")
    if st.session_state.prefs:
        for k, v in st.session_state.prefs.items():
            st.write(f"**{k.upper()}**: {v}")
    else:
        st.caption("Answer a few questions to build your profile here.")
    if st.button("Reset"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# -------------------------------------------------------------------
# RENDER EXISTING CHAT MESSAGES
# -------------------------------------------------------------------
for msg in st.session_state.messages:
    bubble_class = "assistant-bubble" if msg["role"] == "assistant" else "user-bubble"
    with st.chat_message(msg["role"]):
        st.markdown(f"<div class='{bubble_class}'>{msg['content']}</div>", unsafe_allow_html=True)

# -------------------------------------------------------------------
# MODE: GUIDE ME TO CHOOSE A CAR
# -------------------------------------------------------------------
if st.session_state.mode == "choose":

    QUESTIONS = {
        "q1": "Is this your first car?",
        "q2": "Who will drive the car most of the time (you, family member, chauffeur)?",
        "q3": "What’s your budget range? (e.g. ₹6–8 lakh, ₹10–12 lakh)",
        "q4": "Which city will you mainly use the car in?",
        "q5": "How many people usually travel in the car?",
        "q6": "On average, how many km do you drive per day?",
        "q7": "Is your usage mostly city, highway, or a mix of both?",
        "q8": "How are the roads typically (smooth, rough, lots of speed breakers)?",
        "q9": "Any fuel preference (Petrol / Diesel / CNG / Electric), or open to suggestions?",
        "q10": "Do you prefer manual or automatic transmission?",
        "q11": "What matters most to you: mileage, safety, comfort, features, or low maintenance?",
    }

    # ---- Question asking phase ----
    if st.session_state.stage in QUESTIONS:
        question = QUESTIONS[st.session_state.stage]

        with st.chat_message("assistant"):
            st.markdown(f"<div class='assistant-bubble'>{question}</div>", unsafe_allow_html=True)

        user_text = st.chat_input("Your answer...")
        if user_text:
            st.session_state.messages.append({"role": "user", "content": user_text})
            st.session_state.prefs[st.session_state.stage] = user_text

            q_idx = int(st.session_state.stage[1:])
            if q_idx >= len(QUESTIONS):
                st.session_state.stage = "reco"
            else:
                st.session_state.stage = f"q{q_idx+1}"
            st.rerun()

    # ---- Initial recommendation phase ----
    elif st.session_state.stage == "reco":
        with st.chat_message("assistant"):
            with st.spinner("Analyzing your needs and shortlisting cars..."):
                msgs = [{"role": "system", "content": CONSULTANT_PROMPT}] + st.session_state.messages
                raw = call_llm(msgs)
            if not raw:
                st.error("⚠️ LLM call failed. Please try again.")
                st.stop()

            st.session_state.raw_reco = raw
            st.session_state.reco_json = extract_json(raw)

            if st.session_state.reco_json:
                st.session_state.messages.append(
                    {"role": "assistant", "content": "Here are some cars that fit you best:"}
                )
            else:
                # Fallback: just show raw text
                st.session_state.messages.append({"role": "assistant", "content": raw})

        st.session_state.stage = "show_reco"
        st.rerun()

    # ---- Show recommendations + alternatives + follow-up ----
    elif st.session_state.stage == "show_reco":
        data = st.session_state.reco_json

        # If JSON parsed → render nice cards
        if data and isinstance(data, dict) and "cars" in data:
            cars = data.get("cars", [])
            cheaper = data.get("cheaper_alternatives", [])
            premium = data.get("premium_alternatives", [])
            followup_q = data.get("followup_question")

            for car in cars:
                name = car.get("name", "Car")
                seg = car.get("segment", "")
                summary = car.get("summary", "")
                pros = car.get("pros", [])
                cons = car.get("cons", [])
                ideal = car.get("ideal_for", "")
                price_band = car.get("price_band", "")

                with st.chat_message("assistant"):
                    st.markdown(
                        f"""
                        <div class='car-card'>
                            <h4 style='margin-bottom:2px;'>{name}</h4>
                            <div style='font-size:0.9rem;color:#555;'>{seg}</div>
                            <div style='font-size:0.85rem;color:#777;'>{price_band}</div>
                            <p style='margin-top:8px;font-size:0.9rem;'>{summary}</p>
                            <b>Pros:</b>
                            <ul>{''.join([f"<li>{p}</li>" for p in pros])}</ul>
                            <b>Cons:</b>
                            <ul>{''.join([f"<li>{c}</li>" for c in cons])}</ul>
                            <b>Best for:</b> {ideal}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

            # Alternatives buttons (just re-trigger recommendation with new intent)
            with st.chat_message("assistant"):
                cols = st.columns(2)
                if cheaper:
                    if cols[0].button("🔽 Show Cheaper Alternatives"):
                        st.session_state.messages.append(
                            {"role": "user", "content": "Can you show me cheaper alternatives?"}
                        )
                        st.session_state.stage = "reco"
                        st.rerun()
                if premium:
                    if cols[1].button("🔼 Show Premium Alternatives"):
                        st.session_state.messages.append(
                            {"role": "user", "content": "Can you show me premium alternatives?"}
                        )
                        st.session_state.stage = "reco"
                        st.rerun()

            # Show follow-up question from JSON once
            if followup_q:
                with st.chat_message("assistant"):
                    st.markdown(
                        f"<div class='assistant-bubble'>{followup_q}</div>",
                        unsafe_allow_html=True,
                    )

        else:
            # JSON failed → just show raw text once
            with st.chat_message("assistant"):
                st.markdown(
                    f"<div class='assistant-bubble'>{st.session_state.raw_reco}</div>",
                    unsafe_allow_html=True,
                )

        # Free-form follow-up from user
        follow_input = st.chat_input("Ask a follow-up or refine your requirements...")
        if follow_input:
            st.session_state.messages.append({"role": "user", "content": follow_input})
            with st.chat_message("assistant"):
                with st.spinner("Let me refine things for you..."):
                    msgs = [{"role": "system", "content": CONSULTANT_PROMPT}] + st.session_state.messages
                    reply = call_llm(msgs)
                if reply:
                    st.session_state.messages.append({"role": "assistant", "content": reply})
                    st.markdown(f"<div class='assistant-bubble'>{reply}</div>", unsafe_allow_html=True)
            st.rerun()

# -------------------------------------------------------------------
# MODE: COMPARE MODELS (SIDE-BY-SIDE WHEN POSSIBLE)
# -------------------------------------------------------------------
elif st.session_state.mode == "compare":

    if st.session_state.stage == "ask_models":
        with st.chat_message("assistant"):
            st.markdown(
                "<div class='assistant-bubble'>Which two car models do you want to compare? (e.g. Baleno vs i20)</div>",
                unsafe_allow_html=True,
            )
        user_text = st.chat_input("Type models to compare...")
        if user_text:
            st.session_state.messages.append({"role": "user", "content": user_text})
            st.session_state.stage = "run_compare"
            st.rerun()

    elif st.session_state.stage == "run_compare":
        with st.chat_message("assistant"):
            with st.spinner("Comparing models for you..."):
                msgs = [{"role": "system", "content": COMPARE_PROMPT}] + st.session_state.messages
                raw = call_llm(msgs)

        data = extract_json(raw)
        if not data:
            # Fallback: just show raw text
            with st.chat_message("assistant"):
                st.markdown(f"<div class='assistant-bubble'>{raw}</div>", unsafe_allow_html=True)
        else:
            cars = data.get("cars", [])
            winner = data.get("winner", "")
            reason = data.get("reason", "")

            if len(cars) >= 2:
                col1, col2 = st.columns(2)
                for car, col in zip(cars[:2], [col1, col2]):
                    with col:
                        st.markdown(
                            f"""
                            <div class='car-card'>
                                <h4>{car.get('name','')}</h4>
                                <b>Pros:</b>
                                <ul>{''.join([f"<li>{p}</li>" for p in car.get('pros',[])])}</ul>
                                <b>Cons:</b>
                                <ul>{''.join([f"<li>{c}</li>" for c in car.get('cons',[])])}</ul>
                                <p><b>Verdict:</b> {car.get('summary','')}</p>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                with st.chat_message("assistant"):
                    st.markdown(
                        f"<div class='assistant-bubble'>🏆 <b>Winner:</b> {winner}<br>{reason}</div>",
                        unsafe_allow_html=True,
                    )

        st.session_state.stage = "compare_followup"

    elif st.session_state.stage == "compare_followup":
        user_text = st.chat_input("Ask about another comparison or follow-up...")
        if user_text:
            st.session_state.messages.append({"role": "user", "content": user_text})
            st.session_state.stage = "run_compare"
            st.rerun()

# -------------------------------------------------------------------
# MODE: BUYING TIPS
# -------------------------------------------------------------------
elif st.session_state.mode == "tips":

    TIPS_QUESTIONS = {
        "tq1": "Who are you buying the car for? (yourself, parents, family, etc.)",
        "tq2": "How would you describe the driving style? (calm, spirited, mix)",
        "tq3": "Roughly how many km do you drive per day?",
        "tq4": "What are your top priorities? (mileage, safety, comfort, features, low maintenance)",
    }

    if st.session_state.stage in TIPS_QUESTIONS:
        q = TIPS_QUESTIONS[st.session_state.stage]
        with st.chat_message("assistant"):
            st.markdown(f"<div class='assistant-bubble'>{q}</div>", unsafe_allow_html=True)
        user_text = st.chat_input("Your answer...")
        if user_text:
            st.session_state.messages.append({"role": "user", "content": user_text})
            st.session_state.prefs[st.session_state.stage] = user_text
            idx = int(st.session_state.stage[2:])
            if idx >= len(TIPS_QUESTIONS):
                st.session_state.stage = "give_tips"
            else:
                st.session_state.stage = f"tq{idx+1}"
            st.rerun()

    elif st.session_state.stage == "give_tips":
        with st.chat_message("assistant"):
            with st.spinner("Preparing some helpful tips for you..."):
                msgs = [{"role": "system", "content": TIPS_PROMPT}] + st.session_state.messages
                reply = call_llm(msgs)
            if reply:
                st.session_state.messages.append({"role": "assistant", "content": reply})
                st.markdown(f"<div class='assistant-bubble'>{reply}</div>", unsafe_allow_html=True)
        st.session_state.stage = "tips_followup"

    elif st.session_state.stage == "tips_followup":
        user_text = st.chat_input("Any other doubts about buying a car?")
        if user_text:
            st.session_state.messages.append({"role": "user", "content": user_text})
            st.session_state.stage = "give_tips"
            st.rerun()
