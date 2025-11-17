###############################################################
# Spinny AI Car Consultant - ChatGPT Style UI
###############################################################

import re
import streamlit as st

from core.schemas import UserPreferences
from core.question_planner import get_next_question
from core.intent_router import route_intent
from core.recommend_engine import get_recommendations
from core.compare_engine import compare_cars
from core.tips_engine import get_tips


# ------------------------------------------------------------
# PAGE CONFIG
# ------------------------------------------------------------
st.set_page_config(
    page_title="Spinny AI Car Consultant",
    page_icon="🚗",
    layout="wide",
)

# ------------------------------------------------------------
# CHATGPT-LIKE CSS
# ------------------------------------------------------------
st.markdown(
    """
<style>
/* Overall background */
body, .main {
    background-color: #f7f7f8 !important;
}

/* Center main content */
.block-container {
    max-width: 900px !important;
    margin: 0 auto !important;
    padding-top: 1.5rem !important;
}

/* Assistant bubble */
.chat-bubble-assistant {
    background: #ffffff;
    color: #111111;
    padding: 12px 16px;
    border-radius: 12px;
    border: 1px solid #e5e7eb;
    margin-bottom: 8px;
    max-width: 80%;
    box-shadow: 0px 1px 3px rgba(0,0,0,0.08);
}

/* User bubble */
.chat-bubble-user {
    background: #e11b22;
    color: #ffffff;
    padding: 12px 16px;
    border-radius: 12px;
    margin-bottom: 8px;
    margin-left: auto;
    max-width: 80%;
    box-shadow: 0px 1px 3px rgba(0,0,0,0.15);
}

/* Car card (inside assistant messages) */
.car-card {
    background: #ffffff;
    border-radius: 12px;
    border: 1px solid #e5e7eb;
    padding: 12px 14px;
    margin: 6px 0;
}

/* Chat input styling only (keep default position) */
div[data-testid="stChatInputContainer"] {
    border-top: 1px solid #e5e7eb;
    background: #ffffff;
}
div[data-testid="stChatInputContainer"] textarea {
    border-radius: 999px !important;
}
</style>
""",
    unsafe_allow_html=True,
)

# ------------------------------------------------------------
# SESSION STATE INIT
# ------------------------------------------------------------
def init_state():
    if "mode" not in st.session_state:
        st.session_state.mode = "Guide me"
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "prefs" not in st.session_state:
        st.session_state.prefs = UserPreferences()
    if "compare_models" not in st.session_state:
        st.session_state.compare_models = []
    if "initial_greeting_shown" not in st.session_state:
        st.session_state.initial_greeting_shown = False

init_state()

# ------------------------------------------------------------
# SIDEBAR - MODE + PROFILE
# ------------------------------------------------------------
with st.sidebar:
    st.markdown("### Mode")
    mode_choice = st.radio(
        "",
        ["Guide me", "Compare models", "Car buying tips"],
        index=["Guide me", "Compare models", "Car buying tips"].index(
            st.session_state.mode
        ),
    )

    # If mode changed, reset conversation (fresh chat feel)
    if mode_choice != st.session_state.mode:
        st.session_state.mode = mode_choice
        st.session_state.messages = []
        st.session_state.compare_models = []
        st.session_state.initial_greeting_shown = False

    st.markdown("---")
    st.markdown("### Profile (Guide mode)")
    prefs_dict = st.session_state.prefs.dict()
    has_any_pref = False
    for k, v in prefs_dict.items():
        if v:
            has_any_pref = True
            st.write(f"**{k.replace('_',' ').title()}**: {v}")
    if not has_any_pref:
        st.caption("As you answer, I'll remember your preferences here.")

    if st.button("Reset all"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        init_state()
        st.experimental_rerun()

# ------------------------------------------------------------
# HEADER
# ------------------------------------------------------------
if st.session_state.mode == "Guide me":
    st.markdown("## 🚗 Spinny AI – Car Buying Guide")
    st.caption("Chat with me to figure out the best car for your needs.")
elif st.session_state.mode == "Compare models":
    st.markdown("## ⚖️ Spinny AI – Compare Car Models")
    st.caption("Tell me which cars you want to compare.")
else:
    st.markdown("## 💡 Spinny AI – Car Buying Tips")
    st.caption("Ask for general guidance, tips, and what to watch out for.")

st.markdown("---")

# ------------------------------------------------------------
# RENDER CHAT HISTORY
# ------------------------------------------------------------
for msg in st.session_state.messages:
    bubble_class = "chat-bubble-assistant" if msg["role"] == "assistant" else "chat-bubble-user"
    with st.chat_message(msg["role"]):
        st.markdown(f"<div class='{bubble_class}'>{msg['content']}</div>", unsafe_allow_html=True)

# ------------------------------------------------------------
# HELPER: APPEND ASSISTANT MESSAGE
# ------------------------------------------------------------
def assistant_say(text: str):
    st.session_state.messages.append({"role": "assistant", "content": text})
    with st.chat_message("assistant"):
        st.markdown(f"<div class='chat-bubble-assistant'>{text}</div>", unsafe_allow_html=True)

# ------------------------------------------------------------
# INITIAL GREETING PER MODE (only once)
# ------------------------------------------------------------
if not st.session_state.initial_greeting_shown:
    if st.session_state.mode == "Guide me":
        assistant_say(
            "Hi! I’m your Spinny AI car consultant. Tell me a bit about your budget, city, and how you’ll use the car."
        )
    elif st.session_state.mode == "Compare models":
        assistant_say(
            "Sure, I can compare cars. Type something like: **\"Baleno vs i20 vs Altroz\"**."
        )
    else:
        assistant_say(
            "Ask me anything about buying a car – new vs used, test-drive tips, negotiation, maintenance, etc."
        )
    st.session_state.initial_greeting_shown = True

# ------------------------------------------------------------
# HANDLERS FOR EACH MODE
# ------------------------------------------------------------
def handle_guide_message(user_msg: str):
    """Guide-mode: use LLM planner + recommender."""

    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": user_msg})

    # Use your intent router in case user abruptly says "compare X vs Y"
    try:
        intent_info = route_intent(user_msg)
        intent = intent_info.get("intent", "recommend")
    except Exception:
        intent = "recommend"

    # If router says "compare", switch mode
    if intent == "compare":
        st.session_state.mode = "Compare models"
        st.session_state.messages = []  # start fresh in new mode
        st.session_state.initial_greeting_shown = False
        st.experimental_rerun()
        return

    # Build conversation history as plain text for planner
    history_text = "\n".join([m["content"] for m in st.session_state.messages])

    # Call LLM planner
    planner_out = get_next_question(
        st.session_state.prefs, user_msg, history_text
    )

    updated = planner_out.get("updated_preferences", {})
    # Merge into current preferences
    merged = {**st.session_state.prefs.dict(), **updated}
    st.session_state.prefs = UserPreferences(**merged)

    # If planner still wants more info -> just ask next question
    if planner_out.get("need_more_info", True):
        next_q = planner_out.get(
            "next_question",
            "What matters most to you: mileage, safety, comfort, or features?",
        )
        assistant_say(next_q)
        return

    # Otherwise, we have enough info: call recommender
    prefs_dict = st.session_state.prefs.dict()
    with st.chat_message("assistant"):
        with st.spinner("Shortlisting cars for you..."):
            rec = get_recommendations(prefs_dict)

    # Display recommendations
    cars = rec.get("cars", [])
    if not cars:
        assistant_say("I'm having trouble finding options right now. Try changing budget or fuel preference.")
    else:
        for car in cars:
            name = car.get("name", "Car")
            summary = car.get("summary", "")
            pros = car.get("pros", [])
            cons = car.get("cons", [])

            html = f"""
            <div class="chat-bubble-assistant">
                <div class="car-card">
                    <b>{name}</b><br>
                    <p>{summary}</p>
                    <b>Pros:</b>
                    <ul>{''.join(f'<li>{p}</li>' for p in pros)}</ul>
                    <b>Cons:</b>
                    <ul>{''.join(f'<li>{c}</li>' for c in cons)}</ul>
                </div>
            </div>
            """
            st.session_state.messages.append({"role": "assistant", "content": html})
            with st.chat_message("assistant"):
                st.markdown(html, unsafe_allow_html=True)

    # Follow-up question
    fu = rec.get(
        "followup_question",
        "Would you like to refine these options, compare some of them, or change your budget/requirements?",
    )
    assistant_say(fu)


def handle_compare_message(user_msg: str):
    """Compare-mode: parse models and call compare engine."""

    st.session_state.messages.append({"role": "user", "content": user_msg})

    # Extract model names from user message: split by comma or "vs"
    tokens = [x.strip() for x in re.split(r",|vs|VS|Vs", user_msg) if x.strip()]
    if not tokens:
        assistant_say("Please mention the car models, like: `Baleno vs i20 vs Altroz`.")
        return

    models = tokens[:4]  # limit to 4 cars
    st.session_state.compare_models = models

    with st.chat_message("assistant"):
        with st.spinner("Comparing these cars for you..."):
            comp = compare_cars(models)

    cars = comp.get("cars", [])
    best = comp.get("best_overall", "")

    if not cars:
        assistant_say("I couldn't generate a comparison. Try rephrasing the models.")
        return

    # Side-by-side style using columns
    cols = st.columns(len(cars))
    for idx, car in enumerate(cars):
        with cols[idx]:
            html = f"""
            <div class="car-card">
                <b>{car.get('name','Car')}</b><br>
                <p>{car.get('summary','')}</p>
                <b>Pros:</b>
                <ul>{''.join(f'<li>{p}</li>' for p in car.get('pros',[]))}</ul>
                <b>Cons:</b>
                <ul>{''.join(f'<li>{c}</li>' for c in car.get('cons',[]))}</ul>
            </div>
            """
            st.markdown(html, unsafe_allow_html=True)

    if best:
        assistant_say(f"🏆 Overall, **{best}** looks like the better pick for most buyers.")

    assistant_say(
        "You can ask follow-ups like *'Which is safer?'*, *'Show cheaper alternatives'*, or compare another set of cars."
    )


def handle_tips_message(user_msg: str):
    """Tips-mode: general advice."""

    st.session_state.messages.append({"role": "user", "content": user_msg})

    # You can pass full history or just last msg; here we use history
    context = "\n".join([m["content"] for m in st.session_state.messages])
    with st.chat_message("assistant"):
        with st.spinner("Preparing some tips for you..."):
            tips = get_tips(context)

    assistant_say(tips)
    assistant_say("Feel free to ask more specific questions, like resale value, service costs, or long-term reliability.")

# ------------------------------------------------------------
# MAIN CHAT INPUT (always visible)
# ------------------------------------------------------------
user_input = st.chat_input("Type your message...")

if user_input:
    if st.session_state.mode == "Guide me":
        handle_guide_message(user_input)
    elif st.session_state.mode == "Compare models":
        handle_compare_message(user_input)
    else:
        handle_tips_message(user_input)
