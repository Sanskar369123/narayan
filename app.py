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

    /* COMPARISON CARDS */
    .compare-card {
        background: white;
        padding: 15px;
        border-radius: 12px;
        border: 1px solid #ddd;
        margin-bottom: 12px;
        height: 100%;
    }
    
    .compare-title {
        font-size: 1.2rem;
        font-weight: bold;
        margin-bottom: 10px;
        color: #E11B22;
    }
    
    .badge-winner {
        background: #E11B22;
        color: white;
        padding: 4px 8px;
        border-radius: 6px;
        font-size: 0.8rem;
        margin-top: 10px;
        display: inline-block;
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

IMPORTANT: Return ONLY valid JSON. Do not add any extra text, explanations, or formatting outside the JSON structure.
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

IMPORTANT: Return ONLY valid JSON. Do not add any extra text, explanations, or formatting outside the JSON structure.
Ensure all brackets and quotes are properly closed.
"""

TIPS_PROMPT = """
Generate short, personalised car buying tips based on user answers.
Return plain text suggestions in 6–8 bullet points.
"""


# ---------------- IMPROVED OPENROUTER CALL WITH RETRIES ----------------
def call_llm(messages, max_retries=3):
    payload = {
        "model": "tngtech/deepseek-r1t2-chimera:free",
        "messages": messages,
        "temperature": 0.3,
    }
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    
    for attempt in range(max_retries):
        try:
            r = requests.post(OPENROUTER_URL, headers=headers, data=json.dumps(payload), timeout=30)
            if r.status_code != 200:
                st.error(f"❌ API Error (Attempt {attempt + 1}): HTTP {r.status_code}")
                continue
                
            response_content = r.json()["choices"][0]["message"]["content"]
            
            # Try to validate it's parseable JSON if we expect JSON
            system_content = messages[0]["content"] if messages else ""
            if "COMPARE_PROMPT" in system_content or "CONSULTANT_PROMPT" in system_content:
                json.loads(response_content)  # Test if it's valid JSON
                
            return response_content
            
        except json.JSONDecodeError as e:
            st.warning(f"⚠️ Attempt {attempt + 1}: Received invalid JSON, retrying...")
            if attempt == max_retries - 1:  # Final attempt failed
                st.error(f"❌ Failed to get valid JSON after {max_retries} attempts.")
                return None
        except Exception as e:
            st.error(f"❌ Unexpected error (Attempt {attempt + 1}): {str(e)}")
            return None
    
    return None


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
    st.markdown("## 🚗 Spinny AI Car Advisor")
    st.markdown("### How can I help you today?")

    mode = st.radio(
        "Choose an option",
        ["Guide me to choose a car", "Compare models", "Car buying tips"],
        label_visibility="collapsed"
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
        "q3": "What's your budget? (e.g. 6–8 lakhs)",
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
            st.markdown(f"<div class='assistant-bubble'>{question}</div>", unsafe_allow_html=True)

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

            if raw is None:
                st.error("Sorry, I couldn't generate recommendations at this time. Please try again.")
                st.session_state.stage = "q1"
                st.rerun()

            st.session_state.last_recommendation = raw
            st.session_state.messages.append({"role": "assistant", "content": "Here are your best-fit cars 👇"})
            st.session_state.stage = "follow_up"
            st.rerun()

    # Render recommendation in SPINNY CARD STYLE
    elif st.session_state.stage == "follow_up" and st.session_state.last_recommendation:
        try:
            data = json.loads(st.session_state.last_recommendation)
        except json.JSONDecodeError as e:
            st.error("Sorry, I received an invalid response format. Please try asking again.")
            st.session_state.stage = "q1"
            st.rerun()

        cars = data.get("cars", [])
        cheaper = data.get("cheaper_alternatives", [])
        premium = data.get("premium_alternatives", [])

        # Render each car as a SPINNY card
        for car in cars:
            with st.chat_message("assistant"):
                st.markdown(
                    f"""
                    <div style='background:white;padding:15px;border-radius:12px;border:1px solid #ddd;margin-bottom:12px;'>
                        <h4 style='margin:0;'>{car.get('name', 'Unknown')} </h4>
                        <div style='color:#666;font-size:0.9rem;'>{car.get('segment', '')}</div>
                        <p style='margin-top:8px;font-size:0.9rem;'>{car.get('summary', '')}</p>
                        <b>Pros:</b>
                        <ul>{"".join([f"<li>{p}</li>" for p in car.get('pros', [])])}</ul>
                        <b>Cons:</b>
                        <ul>{"".join([f"<li>{c}</li>" for c in car.get('cons', [])])}</ul>
                        <b>Price:</b> {car.get('price_band', '')}<br>
                        <b>Best for:</b> {car.get('ideal_for', '')}
                    </div>""",
                    unsafe_allow_html=True,
                )

        # Alternative Buttons
        with st.chat_message("assistant"):
            col1, col2 = st.columns(2)
            
            if cheaper:
                with col1:
                    if st.button("🔽 Show Cheaper Alternatives", use_container_width=True):
                        user_q = "Show cheaper alternatives"
                        st.session_state.messages.append({"role": "user", "content": user_q})
                        st.session_state.stage = "alt-cheap"
                        st.rerun()

            if premium:
                with col2:
                    if st.button("🔼 Show Premium Alternatives", use_container_width=True):
                        user_q = "Show premium alternatives"
                        st.session_state.messages.append({"role": "user", "content": user_q})
                        st.session_state.stage = "alt-prem"
                        st.rerun()

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

    if alt_raw is None:
        st.error("Sorry, I couldn't find alternatives at this time. Please try again.")
        st.session_state.stage = "follow_up"
        st.rerun()

    st.session_state.last_recommendation = alt_raw
    st.session_state.stage = "follow_up"
    st.rerun()


# ---------------------------------------------------------------------
#  MODE: COMPARISON (SIDE-BY-SIDE)
# ---------------------------------------------------------------------
if st.session_state.mode == "compare":

    if st.session_state.stage == "ask_models":
        with st.chat_message("assistant"):
            st.markdown("<div class='assistant-bubble'>Which two car models do you want to compare?</div>", unsafe_allow_html=True)
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

        if raw is None:
            st.error("Sorry, I couldn't generate a proper comparison at this time. Please try again.")
            st.session_state.stage = "ask_models"
            st.rerun()

        try:
            data = json.loads(raw)
            
            # Validate the expected structure
            if "cars" not in data or "winner" not in data or "reason" not in data:
                st.error("Received incomplete comparison data. Please try again.")
                st.session_state.stage = "ask_models"
                st.rerun()
                
            cars = data["cars"]
            winner = data["winner"]
            reason = data["reason"]
            
            # Ensure we have at least 2 cars to compare
            if len(cars) < 2:
                st.error("Not enough car data received for comparison. Please try again.")
                st.session_state.stage = "ask_models" 
                st.rerun()

        except json.JSONDecodeError as e:
            st.error("Invalid JSON format from model. Please try the comparison again.")
            st.session_state.stage = "ask_models"
            st.rerun()

        # Render side-by-side comparison
        st.markdown("### 🆚 Comparison Results")
        
        c1, c2 = st.columns(2)
        for i, (container, car) in enumerate(zip([c1, c2], cars)):
            with container:
                is_winner = car.get("name") == winner
                border_color = "#E11B22" if is_winner else "#ddd"
                
                st.markdown(
                    f"""
                    <div class='compare-card' style='border: 2px solid {border_color}'>
                        <div class='compare-title'>{car.get('name', 'Unknown')}</div>
                        {"<div class='badge-winner'>WINNER</div>" if is_winner else ""}
                        
                        <div style='margin: 10px 0;'>
                            <strong>Pros:</strong>
                            <ul style='margin: 5px 0; padding-left: 20px;'>
                                {"".join([f"<li>{p}</li>" for p in car.get('pros', [])])}
                            </ul>
                        </div>
                        
                        <div style='margin: 10px 0;'>
                            <strong>Cons:</strong>
                            <ul style='margin: 5px 0; padding-left: 20px;'>
                                {"".join([f"<li>{c}</li>" for c in car.get('cons', [])])}
                            </ul>
                        </div>
                        
                        <div style='margin-top: 15px;'>
                            <strong>Verdict:</strong><br>
                            {car.get('verdict', '')}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        # Winner summary
        with st.chat_message("assistant"):
            st.markdown(
                f"""
                <div class='assistant-bubble'>
                    <strong>🏆 Winner: {winner}</strong><br><br>
                    <strong>Why it's better:</strong> {reason}
                </div>
                """,
                unsafe_allow_html=True,
            )

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
        "tq2": "What's the driving style?",
        "tq3": "How many km/day?",
        "tq4": "Your priorities?",
    }

    if st.session_state.stage in TIPS_Q:
        q = TIPS_Q[st.session_state.stage]
        with st.chat_message("assistant"):
            st.markdown(f"<div class='assistant-bubble'>{q}</div>", unsafe_allow_html=True)

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
            
            if reply:
                st.markdown(f"<div class='assistant-bubble'>{reply}</div>", unsafe_allow_html=True)
            else:
                st.error("Sorry, I couldn't generate tips at this time. Please try again.")

        st.session_state.stage = "tips_done"

    elif st.session_state.stage == "tips_done":
        user_input = st.chat_input("Any other doubts about buying a car?")
        if user_input:
            st.session_state.messages.append({"role": "user", "content": user_input})
            st.session_state.stage = "give_tips"
            st.rerun()
