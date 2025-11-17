import os
import json
import re
import streamlit as st

from core.schemas import UserPreferences
from core.question_planner import get_next_question
from core.intent_router import route_intent
from core.recommend_engine import get_recommendations
from core.compare_engine import compare_cars
from core.tips_engine import get_tips


# ----------------------------------------------------------
# PAGE CONFIG
# ----------------------------------------------------------
st.set_page_config(page_title="Spinny AI Car Consultant", page_icon="🚗", layout="wide")


# ----------------------------------------------------------
# MODERN CHATGPT-STYLE UI CSS
# ----------------------------------------------------------
st.markdown("""
<style>

body {
    background-color: #F7F7F8;
}

/* Centered content width */
.block-container {
    max-width: 760px !important;
    padding-top: 2rem;
}

/* Chat bubble styles */
.chat-bubble-assistant {
    background: white;
    color: #1A1A1A;
    padding: 14px 18px;
    border-radius: 14px;
    border: 1px solid #E5E7EB;
    margin-bottom: 12px;
    max-width: 85%;
    box-shadow: 0px 1px 3px rgba(0,0,0,0.08);
}

.chat-bubble-user {
    background: #E11B22;
    color: white;
    padding: 14px 18px;
    border-radius: 14px;
    margin-bottom: 12px;
    margin-left: auto;
    max-width: 85%;
    box-shadow: 0px 1px 3px rgba(0,0,0,0.18);
}

/* Streamlit chat input area */
div[data-testid="stChatInputContainer"] {
    border-top: 1px solid #DDD;
    background: white;
    padding: 12px;
}

</style>
""", unsafe_allow_html=True)


# ----------------------------------------------------------
# SESSION STATE INIT
# ----------------------------------------------------------
def init_state():
    if "mode" not in st.session_state:
        st.session_state.mode = None
    if "stage" not in st.session_state:
        st.session_state.stage = "init"
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "prefs" not in st.session_state:
        st.session_state.prefs = UserPreferences()
    if "pending_compare_query" not in st.session_state:
        st.session_state.pending_compare_query = None
    if "generated_tips" not in st.session_state:
        st.session_state.generated_tips = None

init_state()


# ----------------------------------------------------------
# SIDEBAR — CLEAN LOOK
# ----------------------------------------------------------
with st.sidebar:
    st.markdown("### Profile")
    for k, v in st.session_state.prefs.dict().items():
        if v:
            st.write(f"**{k.replace('_', ' ').title()}**: {v}")

    if st.button("Reset"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()


# ----------------------------------------------------------
# RENDER CHAT HISTORY
# ----------------------------------------------------------
for msg in st.session_state.messages:
    bubble = "chat-bubble-assistant" if msg["role"] == "assistant" else "chat-bubble-user"
    with st.chat_message(msg["role"]):
        st.markdown(f"<div class='{bubble}'>{msg['content']}</div>", unsafe_allow_html=True)


# ----------------------------------------------------------
# MODE SELECTION PAGE
# ----------------------------------------------------------
if st.session_state.stage == "init":
    st.markdown("## 🚗 Spinny AI Advisor")
    st.markdown("#### How can I help you today?")

    choice = st.radio(
        "Choose one",
        ["Guide me to choose a car", "Compare models", "Car buying tips"],
        label_visibility="collapsed"
    )

    if st.button("Continue ➡️"):
        if "Guide" in choice:
            st.session_state.mode = "guide"
            st.session_state.stage = "ask_first"
        elif "Compare" in choice:
            st.session_state.mode = "compare"
            st.session_state.stage = "ask_model"
        else:
            st.session_state.mode = "tips"
            st.session_state.stage = "tq1"
        st.rerun()

    st.stop()


# ==========================================================
# MODE 1 — GUIDE MODE (FULL LLM QUESTIONING)
# ==========================================================
if st.session_state.mode == "guide":

    # FIRST QUESTION
    if st.session_state.stage == "ask_first":
        q = "Let's get started! What's your approximate budget?"
        st.session_state.messages.append({"role": "assistant", "content": q})
        with st.chat_message("assistant"):
            st.markdown(f"<div class='chat-bubble-assistant'>{q}</div>", unsafe_allow_html=True)
        st.session_state.stage = "awaiting"
        st.stop()

    # WAIT FOR USER REPLY
    user_msg = st.chat_input("Your answer...")
    if user_msg:

        st.session_state.messages.append({"role": "user", "content": user_msg})

        # INTENT OVERRIDE
        intent = route_intent(user_msg)
        if intent["intent"] == "compare":
            st.session_state.mode = "compare"
            st.session_state.pending_compare_query = user_msg
            st.session_state.stage = "run_compare"
            st.rerun()

        planner_resp = get_next_question(
            st.session_state.prefs,
            user_msg,
            [m["content"] for m in st.session_state.messages]
        )

        # Update preferences
        updated = planner_resp.get("updated_preferences", {})
        current = st.session_state.prefs.dict()
        st.session_state.prefs = UserPreferences(**{**current, **updated})

        # Need more questions → ask next
        if planner_resp.get("need_more_info", False):
            next_q = planner_resp["next_question"]
            st.session_state.messages.append({"role": "assistant", "content": next_q})
            with st.chat_message("assistant"):
                st.markdown(f"<div class='chat-bubble-assistant'>{next_q}</div>", unsafe_allow_html=True)
            st.stop()

        # Otherwise → show recommendations
        st.session_state.stage = "show_reco"
        st.rerun()

    if st.session_state.stage == "show_reco":
        prefs = st.session_state.prefs.dict()
        with st.chat_message("assistant"):
            with st.spinner("Finding cars that match your needs..."):
                data = get_recommendations(prefs)

        # Show recommendations
        for car in data["cars"]:
            with st.chat_message("assistant"):
                st.markdown(f"""
                <div class='chat-bubble-assistant'>
                    <b>{car['name']}</b><br>
                    {car['summary']}<br><br>
                    <b>Pros:</b>
                    <ul>{''.join(f"<li>{p}</li>" for p in car['pros'])}</ul>
                    <b>Cons:</b>
                    <ul>{''.join(f"<li>{c}</li>" for c in car['cons'])}</ul>
                </div>
                """, unsafe_allow_html=True)

        # Follow-up
        fu = data.get("followup_question", "Would you like to refine options further?")
        st.session_state.messages.append({"role": "assistant", "content": fu})
        with st.chat_message("assistant"):
            st.markdown(f"<div class='chat-bubble-assistant'>{fu}</div>", unsafe_allow_html=True)

        st.session_state.stage = "awaiting"
        st.stop()


# ==========================================================
# MODE 2 — COMPARE MODE
# ==========================================================
if st.session_state.mode == "compare":

    # Ask for models
    if st.session_state.stage == "ask_model":
        q = "Which car models should I compare? (example: i20, Baleno, Altroz)"
        st.session_state.messages.append({"role": "assistant", "content": q})
        with st.chat_message("assistant"):
            st.markdown(f"<div class='chat-bubble-assistant'>{q}</div>", unsafe_allow_html=True)
        st.session_state.stage = "await_model"
        st.stop()

    text = st.chat_input("Type your models...")
    if text:
        st.session_state.pending_compare_query = text
        st.session_state.stage = "run_compare"
        st.rerun()

    if st.session_state.stage == "run_compare":
        models = [x.strip() for x in re.split(",|vs", st.session_state.pending_compare_query)]
        models = [m for m in models if m][:4]

        with st.chat_message("assistant"):
            with st.spinner("Comparing..."):
                result = compare_cars(models)

        # Render results
        cars = result.get("cars", [])
        if cars:
            cols = st.columns(len(cars))
            for i, car in enumerate(cars):
                with cols[i]:
                    st.markdown(f"""
                    <div class='chat-bubble-assistant'>
                        <b>{car['name']}</b><br>
                        <b>Pros:</b>
                        <ul>{''.join(f"<li>{p}</li>" for p in car['pros'])}</ul>
                        <b>Cons:</b>
                        <ul>{''.join(f"<li>{c}</li>" for c in car['cons'])}</ul>
                    </div>
                    """, unsafe_allow_html=True)

        # Winner
        win = result.get("best_overall")
        if win:
            with st.chat_message("assistant"):
                st.markdown(f"<div class='chat-bubble-assistant'>🏆 Best overall: <b>{win}</b></div>",
                            unsafe_allow_html=True)

        st.session_state.stage = "compare_follow"
        st.stop()

    if st.session_state.stage == "compare_follow":
        q = "Want me to compare variants or show cheaper/premium rivals?"
        with st.chat_message("assistant"):
            st.markdown(f"<div class='chat-bubble-assistant'>{q}</div>", unsafe_allow_html=True)

        ask = st.chat_input("Ask follow-up...")
        if ask:
            st.session_state.pending_compare_query = ask
            st.session_state.stage = "run_compare"
            st.rerun()


# ==========================================================
# MODE 3 — TIPS MODE
# ==========================================================
if st.session_state.mode == "tips":

    mapping = {
        "tq1": "Who are you buying the car for?",
        "tq2": "What's your driving style?",
        "tq3": "How many km/day?",
        "tq4": "What do you care about the most: mileage, safety, comfort, features, low maintenance?"
    }

    if st.session_state.stage in mapping:
        q = mapping[st.session_state.stage]
        st.session_state.messages.append({"role": "assistant", "content": q})
        with st.chat_message("assistant"):
            st.markdown(f"<div class='chat-bubble-assistant'>{q}</div>", unsafe_allow_html=True)

        ans = st.chat_input("Your answer...")
        if ans:
            st.session_state.messages.append({"role": "user", "content": ans})
            idx = int(st.session_state.stage[2:])
            st.session_state.stage = "run_tips" if idx == 4 else f"tq{idx+1}"
            st.rerun()

    if st.session_state.stage == "run_tips":
        with st.chat_message("assistant"):
            with st.spinner("Preparing personalized tips..."):
                tips = get_tips(" ".join(m["content"] for m in st.session_state.messages))
        st.session_state.generated_tips = tips
        st.session_state.stage = "show_tips"
        st.rerun()

    if st.session_state.stage == "show_tips":
        tips = st.session_state.generated_tips
        st.session_state.messages.append({"role": "assistant", "content": tips})
        with st.chat_message("assistant"):
            st.markdown(f"<div class='chat-bubble-assistant'>{tips}</div>", unsafe_allow_html=True)

        q = "Want more detailed advice?"
        st.session_state.messages.append({"role": "assistant", "content": q})
        with st.chat_message("assistant"):
            st.markdown(f"<div class='chat-bubble-assistant'>{q}</div>", unsafe_allow_html=True)

        st.session_state.stage = "tips_follow"
        st.stop()

    if st.session_state.stage == "tips_follow":
        ask = st.chat_input("Ask follow-up...")
        if ask:
            st.session_state.messages.append({"role": "user", "content": ask})
            st.session_state.stage = "run_tips"
            st.rerun()
