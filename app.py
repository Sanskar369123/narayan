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
from core.followup_engine import (
    answer_reco_followup,
    answer_compare_followup,
)


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
:root {
  --bg:#f4f5fb;
  --card:#ffffff;
  --border:#e4e6ef;
  --primary:#e11b22;
  --text:#111322;
  --muted:#6b7280;
}

body, .main {
  background: radial-gradient(circle at top, #fff 0%, var(--bg) 55%);
  color: var(--text);
}

.block-container {
  max-width: 960px;
  margin: 0 auto;
  padding-top: 1.2rem;
}

.mode-pill > label[data-baseweb="radio"] {
  display:flex;
  gap:0.5rem;
}

.chat-bubble-assistant, .chat-bubble-user {
  width: fit-content;
  max-width: 85%;
  padding: 14px 18px;
  border-radius: 18px;
  border: 1px solid var(--border);
  box-shadow: 0 8px 20px rgba(16, 24, 40, 0.08);
  font-size: 0.95rem;
  line-height: 1.6;
}

.chat-bubble-assistant {
  background: var(--card);
  color: var(--text);
}

.chat-bubble-user {
  background: var(--primary);
  border-color: transparent;
  color: #fff;
  margin-left: auto;
}

.car-card {
  background: linear-gradient(135deg, #fff, #f9fafc);
  border-radius: 16px;
  padding: 16px 18px;
  border: 1px solid var(--border);
  margin-bottom: 0.5rem;
}

.car-card ul {
  padding-left: 1.1rem;
}

.comparison-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 1rem;
  width: 100%;
}

.score-row {
  display: flex;
  justify-content: space-between;
  font-size: 0.85rem;
  color: var(--muted);
  border-bottom: 1px dashed var(--border);
  padding: 2px 0;
}

.stat-card {
  background: var(--card);
  border-radius: 16px;
  padding: 14px 18px;
  border: 1px solid var(--border);
  text-align: left;
}

div[data-testid="stChatInputContainer"] {
  border-top: 1px solid var(--border);
  background: var(--card);
  box-shadow: 0 -10px 30px rgba(15, 23, 42, 0.05);
}
div[data-testid="stChatInputContainer"] textarea {
  border-radius: 999px !important;
  border: 1px solid var(--border);
  padding: 14px 20px !important;
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
    if "guide_stage" not in st.session_state:
        st.session_state.guide_stage = "collect"
    if "last_recommendations" not in st.session_state:
        st.session_state.last_recommendations = None
    if "last_comparison" not in st.session_state:
        st.session_state.last_comparison = None
    if "compare_stage" not in st.session_state:
        st.session_state.compare_stage = "awaiting_models"

init_state()
# --- SAFELY MIGRATE OLD MODES ---
old_modes = {"guide": "Guide me", "compare": "Compare models", "tips": "Car buying tips"}
if st.session_state.mode in old_modes:
    st.session_state.mode = old_modes[st.session_state.mode]


def reset_mode_state(target_mode):
    st.session_state.messages = []
    st.session_state.initial_greeting_shown = False
    if target_mode == "Guide me":
        st.session_state.prefs = UserPreferences()
        st.session_state.guide_stage = "collect"
        st.session_state.last_recommendations = None
    if target_mode == "Compare models":
        st.session_state.compare_models = []
        st.session_state.compare_stage = "awaiting_models"
        st.session_state.last_comparison = None


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
        reset_mode_state(mode_choice)

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
# HEADER / HERO
# ------------------------------------------------------------
with st.container():
    if st.session_state.mode == "Guide me":
        st.markdown("### 🚗 Spinny AI — Personal Car Consultant")
        st.caption("Share your lifestyle, budget, and must-haves. I’ll keep track, nudge for missing details, and refine your shortlist with every reply.")
    elif st.session_state.mode == "Compare models":
        st.markdown("### ⚖️ Spinny AI — Side-by-side comparisons")
        st.caption("Give me up to 4 models (e.g. “Baleno vs i20 vs Altroz”). I’ll rank them by criteria and handle follow-up questions.")
    else:
        st.markdown("### 💡 Spinny AI — Buying tips playbook")
        st.caption("Ask for financing hacks, ownership costs, maintenance schedules or negotiation tips.")

    c1, c2, c3 = st.columns(3)
    c1.markdown(
        """
        <div class="stat-card">
            <div style="font-size:0.85rem;color:#6b7280;">Profiles completed</div>
            <div style="font-size:1.6rem;font-weight:600;">1,200+</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    c2.markdown(
        """
        <div class="stat-card">
            <div style="font-size:0.85rem;color:#6b7280;">Avg shortlist time</div>
            <div style="font-size:1.6rem;font-weight:600;">2m 40s</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    c3.markdown(
        """
        <div class="stat-card">
            <div style="font-size:0.85rem;color:#6b7280;">Comparisons run</div>
            <div style="font-size:1.6rem;font-weight:600;">500+</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("---")

# ------------------------------------------------------------
# RENDER CHAT HISTORY
# ------------------------------------------------------------
for msg in st.session_state.messages:
    bubble_class = "chat-bubble-assistant" if msg["role"] == "assistant" else "chat-bubble-user"
    with st.chat_message(msg["role"]):
        if msg.get("allow_html"):
            st.markdown(msg["content"], unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='{bubble_class}'>{msg['content']}</div>", unsafe_allow_html=True)

# ------------------------------------------------------------
# HELPER: APPEND ASSISTANT MESSAGE
# ------------------------------------------------------------
def assistant_say(text: str, allow_html: bool = False):
    st.session_state.messages.append(
        {"role": "assistant", "content": text, "allow_html": allow_html}
    )
    with st.chat_message("assistant"):
        if allow_html:
            st.markdown(text, unsafe_allow_html=True)
        else:
            st.markdown(
                f"<div class='chat-bubble-assistant'>{text}</div>",
                unsafe_allow_html=True,
            )


def build_comparison_html(cars, criteria):
    cards = []
    for car in cars:
        scores = car.get("scores") or {}
        score_rows = ""
        if criteria:
            score_rows = "".join(
                f"<div class='score-row'><span>{crit.title()}</span><span>{scores.get(crit, 0)}</span></div>"
                for crit in criteria
            )
        card = f"""
        <div class="car-card">
            <b>{car.get('name', 'Car')}</b>
            <p>{car.get('summary') or ''}</p>
            {'<div style="font-size:0.85rem;color:#6b7280;margin-bottom:4px;">Scores</div>' if score_rows else ''}
            {score_rows}
            <b>Pros</b>
            <ul>{''.join(f'<li>{p}</li>' for p in (car.get('pros') or []))}</ul>
            <b>Cons</b>
            <ul>{''.join(f'<li>{c}</li>' for c in (car.get('cons') or []))}</ul>
        </div>
        """
        cards.append(card)

    return f"<div class='chat-bubble-assistant'><div class='comparison-grid'>{''.join(cards)}</div></div>"

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
    st.session_state.messages.append(
        {"role": "user", "content": user_msg, "allow_html": False}
    )

    # Use your intent router in case user abruptly says "compare X vs Y"
    try:
        intent_info = route_intent(user_msg)
        intent = intent_info.get("intent", "recommend")
    except Exception:
        intent_info = {}
        intent = "recommend"

    # If router says "compare", switch mode
    if intent == "compare":
        st.session_state.mode = "Compare models"
        reset_mode_state("Compare models")
        st.experimental_rerun()
        return

    if intent == "restart":
        reset_mode_state("Guide me")
        st.session_state.initial_greeting_shown = False
        assistant_say("All right, let's start fresh! What's your approximate budget range?")
        st.experimental_rerun()
        return

    # Build conversation history as plain text for planner
    history_text = "\n".join([m["content"] for m in st.session_state.messages])

    # Call LLM planner
    planner_out = get_next_question(
        st.session_state.prefs, user_msg, history_text
    )

    updated = planner_out.get("updated_preferences", {}) or {}
    if updated:
        merged = {**st.session_state.prefs.dict(), **updated}
        st.session_state.prefs = UserPreferences(**merged)
        st.session_state.guide_stage = "collect"

    clarification = planner_out.get("clarification_message")
    has_recs_ready = (
        st.session_state.guide_stage == "post_recs"
        and st.session_state.last_recommendations is not None
    )

    if clarification:
        assistant_say(clarification)
        return

    if (
        has_recs_ready
        and not updated
        and not planner_out.get("need_more_info", False)
    ):
        followup_reply = answer_reco_followup(
            st.session_state.prefs.dict(),
            st.session_state.last_recommendations,
            user_msg,
        )
        assistant_say(followup_reply)
        return

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
            st.write("Crunching preferences and recent launches...")
            rec = get_recommendations(prefs_dict)

    st.session_state.last_recommendations = rec
    st.session_state.guide_stage = "post_recs"

    # Display recommendations
    cars = rec.get("cars", [])
    if not cars:
        assistant_say("I'm having trouble finding options right now. Try tweaking your budget or fuel preference.")
    else:
        for car in cars:
            name = car.get("name", "Car")
            summary = car.get("summary") or ""
            pros = car.get("pros") or []
            cons = car.get("cons") or []

            html = f"""
            <div class="chat-bubble-assistant">
                <div class="car-card">
                    <b>{name}</b>
                    <p>{summary}</p>
                    <b>Pros</b>
                    <ul>{''.join(f'<li>{p}</li>' for p in pros)}</ul>
                    <b>Cons</b>
                    <ul>{''.join(f'<li>{c}</li>' for c in cons)}</ul>
                </div>
            </div>
            """
            assistant_say(html, allow_html=True)

    # Follow-up question
    fu = rec.get(
        "followup_question",
        "Want to refine these options, compare two of them, or start over?",
    )
    assistant_say(fu)


def handle_compare_message(user_msg: str):
    """Compare-mode: parse models and call compare engine."""

    st.session_state.messages.append(
        {"role": "user", "content": user_msg, "allow_html": False}
    )

    # Extract model names from user message: split by comma or "vs"
    tokens = [x.strip() for x in re.split(r",|vs|VS|Vs", user_msg) if x.strip()]

    if len(tokens) >= 2:
        models = tokens[:4]  # limit to 4 cars
        st.session_state.compare_models = models

        with st.chat_message("assistant"):
            with st.spinner("Comparing these cars for you..."):
                st.write("Stacking them on mileage, safety, comfort, tech and value...")
                comp = compare_cars(models)

        cars = comp.get("cars", [])
        if not cars:
            assistant_say("I couldn't generate a comparison. Try rephrasing the models.")
            return

        st.session_state.last_comparison = comp
        st.session_state.compare_stage = "post_compare"

        comparison_html = build_comparison_html(cars, comp.get("criteria", []))
        assistant_say(comparison_html, allow_html=True)

        best = comp.get("best_overall")
        notes = comp.get("notes")

        if best:
            assistant_say(f"🏆 Overall, **{best}** looks like the stronger pick for most buyers.")
        if notes:
            assistant_say(notes)

        assistant_say(
            "Ask me follow-ups like “Which one has lower running cost?” or “Suggest safer alternatives”."
        )
        return

    # No fresh models supplied — treat as follow-up if we have context
    if st.session_state.last_comparison:
        followup = answer_compare_followup(st.session_state.last_comparison, user_msg)
        assistant_say(followup)
    else:
        assistant_say("Please mention at least two car models, e.g. `Baleno vs i20`.")


def handle_tips_message(user_msg: str):
    """Tips-mode: general advice."""

    st.session_state.messages.append(
        {"role": "user", "content": user_msg, "allow_html": False}
    )

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
