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
    answer_tips_followup,
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
  align-items:center;
  justify-content:center;
  padding:0.4rem 0.8rem;
  border-radius:999px;
  border:1px solid transparent;
  background:transparent;
  font-size:0.85rem;
  color:var(--muted);
  cursor:pointer;
}

.mode-pill > label[data-baseweb="radio"]:hover {
  background:#f9fafb;
}

.mode-pill > div[data-baseweb="radio"] > input:checked + label {
  background:rgba(225,27,34,0.06);
  color:var(--primary);
  border-color:var(--primary);
  font-weight:600;
}

.chat-bubble-assistant {
  background: var(--card);
  color: var(--text);
  padding: 12px 16px;
  border-radius: 14px;
  border:1px solid var(--border);
  margin-bottom: 8px;
  margin-right:auto;
  max-width: 80%;
  box-shadow: 0 1px 3px rgba(15,23,42,0.04);
  font-size:0.92rem;
}

.chat-bubble-user {
  background: var(--primary);
  color: #ffffff;
  padding: 12px 16px;
  border-radius: 14px;
  margin-bottom: 8px;
  margin-left:auto;
  max-width: 70%;
  box-shadow: 0 2px 6px rgba(15,23,42,0.25);
  font-size:0.92rem;
}

.car-card {
  background: #ffffff;
  border-radius: 12px;
  border:1px solid var(--border);
  padding: 12px 14px;
  margin: 6px 0;
}

.car-card h4 {
  margin:0 0 4px 0;
  font-size:0.98rem;
}

.car-card p {
  margin:4px 0;
  font-size:0.9rem;
}

.comparison-grid {
  display:grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap:0.75rem;
}

.comparison-grid .car-card {
  height:100%;
}

/* chat input container */
div[data-testid="stChatInputContainer"] {
  border-top:1px solid var(--border);
  background:#ffffff;
}
div[data-testid="stChatInputContainer"] textarea {
  border-radius:999px !important;
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
        key="mode_radio",
    )

    if mode_choice != st.session_state.mode:
        st.session_state.mode = mode_choice
        reset_mode_state(mode_choice)

    st.markdown("---")
    if st.session_state.mode == "Guide me":
        st.markdown("### Your profile")
        prefs_dict = st.session_state.prefs.dict()
        any_pref = False
        for k, v in prefs_dict.items():
            if v:
                any_pref = True
                st.write(f"**{k.replace('_',' ').title()}**: {v}")
        if not any_pref:
            st.caption("As you answer, I’ll remember your preferences here.")
    else:
        st.markdown("### Quick actions")
        st.caption("Ask follow-ups like:")
        if st.session_state.mode == "Compare models":
            st.markdown("- Which is safer?\n- Show cheaper alternatives\n- City vs highway usage")
        else:
            st.markdown("- New vs used?\n- How to test drive?\n- Maintenance & resale tips")

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
    st.caption("I’ll ask a few simple questions, then shortlist cars for you.")
elif st.session_state.mode == "Compare models":
    st.markdown("## ⚖️ Spinny AI – Compare Car Models")
    st.caption("Tell me which cars you want to compare, I’ll break it down clearly.")
else:
    st.markdown("## 💡 Spinny AI – Car Buying Tips")
    st.caption("Ask anything about how to choose, test drive, negotiate, or maintain a car.")

# Some tiny stats row
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(
        """
        <div class="stat-card">
            <div style="font-size:0.85rem;color:#6b7280;">Helped buyers</div>
            <div style="font-size:1.6rem;font-weight:600;">10K+</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with c2:
    st.markdown(
        """
        <div class="stat-card">
            <div style="font-size:0.85rem;color:#6b7280;">Avg. consult time</div>
            <div style="font-size:1.6rem;font-weight:600;">3–5 min</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with c3:
    st.markdown(
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
    bubble_class = (
        "chat-bubble-assistant" if msg["role"] == "assistant" else "chat-bubble-user"
    )
    content = msg.get("content", "")
    allow_html = msg.get("allow_html", False)
    with st.chat_message(msg["role"]):
        if allow_html:
            st.markdown(content, unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='{bubble_class}'>{content}</div>", unsafe_allow_html=True)

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
            st.markdown(f"<div class='chat-bubble-assistant'>{text}</div>", unsafe_allow_html=True)

def build_comparison_html(cars, criteria):
    cards = []
    for car in cars:
        name = car.get("name", "Car")
        summary = car.get("summary", "")
        pros = car.get("pros", [])
        cons = car.get("cons", [])

        card = f"""
        <div class="car-card">
            <h4>{name}</h4>
            <p>{summary}</p>
            <b>Pros</b>
            <ul>{''.join(f'<li>{p}</li>' for p in pros)}</ul>
            <b>Cons</b>
            <ul>{''.join(f'<li>{c}</li>' for c in cons)}</ul>
        </div>
        """
        cards.append(card)

    return f"<div class='chat-bubble-assistant'><div class='comparison-grid'>{''.join(cards)}</div></div>"

# ------------------------------------------------------------
# INITIAL GREETING PER MODE (only once) – PATCHED
# ------------------------------------------------------------
if not st.session_state.initial_greeting_shown:
    if st.session_state.mode == "Guide me":
        assistant_say(
            "Hi! I’m your Spinny AI car consultant. To start, what's your approximate budget range?"
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

    updated = planner_out.get("updated_preferences", {})
    merged = {**st.session_state.prefs.dict(), **updated}
    st.session_state.prefs = UserPreferences(**merged)

    # Clarification message from planner (optional)
    clar_msg = planner_out.get("clarification_message", "")
    if clar_msg:
        assistant_say(clar_msg)
        return

    # Need more questions
    if planner_out.get("need_more_info", True):
        next_q = planner_out.get(
            "next_question",
            "What matters most to you: mileage, safety, comfort, or features?",
        )
        assistant_say(next_q)
        return

    # Otherwise, we have enough info: call recommender
    prefs_dict = st.session_state.prefs.dict()
    st.session_state.guide_stage = "recommend"
    with st.chat_message("assistant"):
        with st.spinner("Shortlisting cars for you..."):
            st.write("Crunching preferences and recent launches...")
            rec = get_recommendations(prefs_dict)

    st.session_state.last_recommendations = rec

    cars = rec.get("cars", [])
    if not cars:
        assistant_say(
            "Hmm, I'm not finding clear matches yet. Try tweaking budget or fuel / transmission preference."
        )
    else:
        for car in cars:
            name = car.get("name", "Car")
            summary = car.get("summary", "")
            pros = car.get("pros", [])
            cons = car.get("cons", [])
            html = f"""
            <div class="car-card">
                <h4>{name}</h4>
                <p>{summary}</p>
                <b>Pros</b>
                <ul>{''.join(f'<li>{p}</li>' for p in pros)}</ul>
                <b>Cons</b>
                <ul>{''.join(f'<li>{c}</li>' for c in cons)}</ul>
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

    # If we already have a comparison and this looks like a follow-up:
    if st.session_state.compare_stage == "post_compare" and st.session_state.last_comparison:
        follow = answer_compare_followup(
            user_msg,
            st.session_state.last_comparison,
        )
        if follow:
            assistant_say(follow)
            return

    # Extract model names from user message: split by comma or "vs"
    tokens = [x.strip() for x in re.split(r",|vs|VS|Vs", user_msg) if x.strip()]
    if not tokens:
        assistant_say("Please mention the car models, like: `Baleno vs i20 vs Altroz`.")
        return

    models = tokens[:4]
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
    if best:
        assistant_say(f"🏆 Overall, **{best}** looks like the safer bet for most buyers.")

    assistant_say(
        "You can now ask things like *\"Which is safer?\"*, *\"Show cheaper rivals\"*, or share your usage so I can tune the advice."
    )


def handle_tips_message(user_msg: str):
    """Tips-mode: general advice with follow-ups."""

    st.session_state.messages.append(
        {"role": "user", "content": user_msg, "allow_html": False}
    )

    # If we already gave tips, try follow-up engine
    if st.session_state.generated_tips:
        follow = answer_tips_followup(
            user_msg,
            st.session_state.generated_tips,
        )
        if follow:
            assistant_say(follow)
            return

    context = "\n".join([m["content"] for m in st.session_state.messages])
    with st.chat_message("assistant"):
        with st.spinner("Preparing some tips for you..."):
            tips = get_tips(context)

    st.session_state.generated_tips = tips
    assistant_say(tips)
    assistant_say(
        "You can ask more specific things like *\"New vs used?\"*, *\"How to check a used car?\"* or *\"How to do a proper test drive?\"*"
    )

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
