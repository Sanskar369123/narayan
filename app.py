###############################################################
# SPINNY AI CAR CONSULTANT – UPDATED WITH QUESTION PLANNER
###############################################################

import os
import json
import streamlit as st
import re

# 🔥 Import new modular logic
from core.schemas import UserPreferences
from core.question_planner import get_next_question
from core.intent_router import route_intent
from core.recommend_engine import get_recommendations
from core.compare_engine import compare_cars
from core.tips_engine import get_tips

###############################################################
# BASIC CONFIG
###############################################################
st.set_page_config(
    page_title="Spinny AI Car Consultant",
    page_icon="🚗",
    layout="centered"
)

###############################################################
# PREMIUM CHAT UI CSS
###############################################################
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
</style>
""", unsafe_allow_html=True)

###############################################################
# SESSION STATE SETUP
###############################################################
def init_state():
    defaults = dict(
        mode=None,
        stage="init",
        messages=[],
        pref_obj=UserPreferences(),
        pending_compare_query=None,
        generated_tips=None,
    )
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

###############################################################
# SIDEBAR – PROFILE
###############################################################
with st.sidebar:
    st.markdown("### Your Profile")
    pref = st.session_state.pref_obj.dict()
    for k, v in pref.items():
        if v is not None:
            st.write(f"**{k.replace('_',' ').title()}**: {v}")

    if st.button("Reset"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

###############################################################
# RENDER CHAT HISTORY
###############################################################
for msg in st.session_state.messages:
    role = msg["role"]
    bubble = "assistant-bubble" if role == "assistant" else "user-bubble"
    with st.chat_message(role):
        st.markdown(f"<div class='{bubble}'>{msg['content']}</div>", unsafe_allow_html=True)

###############################################################
# INITIAL MODE SELECTION
###############################################################
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
            st.session_state.stage = "ask_first"
        elif "Compare" in mode:
            st.session_state.mode = "compare"
            st.session_state.stage = "ask_compare"
        else:
            st.session_state.mode = "tips"
            st.session_state.stage = "tq1"
        st.rerun()

    st.stop()

###############################################################
# UNIVERSAL FOLLOW-UP DISPLAY
###############################################################
def show_followup(text, mode):
    fallback = {
        "guide": "Would you like me to refine your options further?",
        "compare": "Want me to compare variants or show cheaper/premium rivals?",
        "tips": "Would you like more detailed tips?",
    }
    if not text:
        text = fallback.get(mode, "What would you like to do next?")
    
    with st.chat_message("assistant"):
        st.markdown(f"<div class='assistant-bubble'>{text}</div>", unsafe_allow_html=True)
    st.session_state.messages.append({"role": "assistant", "content": text})

###############################################################
# MODE 1 — GUIDE MODE (PLANNER DRIVEN)
###############################################################
if st.session_state.mode == "choose":

    # 👉 Step 0: Ask first question
    if st.session_state.stage == "ask_first":
        q = "Great! Let’s start simple — what's your approximate budget?"
        with st.chat_message("assistant"):
            st.markdown(f"<div class='assistant-bubble'>{q}</div>", unsafe_allow_html=True)
        st.session_state.messages.append({"role": "assistant", "content": q})
        st.session_state.stage = "awaiting_user"
        st.stop()

    # 👉 Step 1: Wait for user input
    user_message = st.chat_input("Your answer...")

    if user_message:
        st.session_state.messages.append({"role": "user", "content": user_message})

        # 🧠 INTENT ROUTER (user may suddenly want to compare)
        intent = route_intent(user_message)
        if intent["intent"] == "compare":
            st.session_state.mode = "compare"
            st.session_state.pending_compare_query = user_message
            st.session_state.stage = "run_compare"
            st.rerun()

        # 🧠 QUESTION PLANNER
        planner = get_next_question(st.session_state.pref_obj, user_message)

        # Update preferences
        updated_prefs = planner["updated_preferences"]
        st.session_state.pref_obj = UserPreferences(
            **{**st.session_state.pref_obj.dict(), **updated_prefs}
        )

        # If planner says need more info → Ask next question
        if planner["need_more_info"]:
            next_q = planner["next_question"]
            with st.chat_message("assistant"):
                st.markdown(f"<div class='assistant-bubble'>{next_q}</div>", unsafe_allow_html=True)
            st.session_state.messages.append({"role": "assistant", "content": next_q})
            st.stop()

        # Otherwise → Go to recommendation
        st.session_state.stage = "show_reco"
        st.rerun()

    # 👉 Step 3: Show recommendations
    if st.session_state.stage == "show_reco":
        prefs = st.session_state.pref_obj.dict()
        with st.chat_message("assistant"):
            with st.spinner("Finding the best cars for you..."):
                rec = get_recommendations(prefs)

        # Display car cards
        for car in rec.get("cars", []):
            with st.chat_message("assistant"):
                st.markdown(f"""
                <div class='car-card'>
                    <h4>{car['name']}</h4>
                    <p>{car['summary']}</p>
                    <b>Pros:</b>
                    <ul>{''.join(f"<li>{p}</li>" for p in car['pros'])}</ul>
                    <b>Cons:</b>
                    <ul>{''.join(f"<li>{c}</li>" for c in car['cons'])}</ul>
                </div>""", unsafe_allow_html=True)

        # Follow-up question
        fu = rec.get("followup_question", "")
        show_followup(fu, "guide")

        st.session_state.stage = "awaiting_user"
        st.stop()

###############################################################
# MODE 2 — COMPARE MODE
###############################################################
elif st.session_state.mode == "compare":

    # Step 1: Ask which cars to compare
    if st.session_state.stage == "ask_compare":
        with st.chat_message("assistant"):
            st.markdown("<div class='assistant-bubble'>Which cars do you want me to compare?</div>", unsafe_allow_html=True)

        text = st.chat_input("Eg: Baleno, i20, Altroz")
        if text:
            st.session_state.pending_compare_query = text
            st.session_state.stage = "run_compare"
            st.rerun()

    # Step 2: Run comparison
    elif st.session_state.stage == "run_compare":
        text = st.session_state.pending_compare_query
        models = [x.strip() for x in re.split(",|vs", text) if x.strip()][:4]

        with st.chat_message("assistant"):
            with st.spinner("Comparing..."):
                comp = compare_cars(models)

        # Display comparison (generic table)
        cars = comp.get("cars", [])
        criteria = comp.get("criteria", [])

        if cars:
            cols = st.columns(len(cars))
            for i, car in enumerate(cars):
                with cols[i]:
                    st.markdown(f"""
                    <div class='car-card'>
                        <h4>{car['name']}</h4>
                        <p>{car['summary']}</p>
                        <b>Pros:</b>
                        <ul>{''.join(f"<li>{p}</li>" for p in car['pros'])}</ul>
                        <b>Cons:</b>
                        <ul>{''.join(f"<li>{c}</li>" for c in car['cons'])}</ul>
                    </div>
                    """, unsafe_allow_html=True)

        # Best overall
        with st.chat_message("assistant"):
            st.markdown(f"<div class='assistant-bubble'>🏆 Best overall: {comp.get('best_overall')}</div>", unsafe_allow_html=True)

        # Follow-up
        show_followup("Want me to compare variants or show cheaper/premium rivals?", "compare")

        st.session_state.stage = "compare_loop"
        st.stop()

    # Step 3: Follow-up loop
    elif st.session_state.stage == "compare_loop":
        ask = st.chat_input("Ask more...")
        if ask:
            st.session_state.pending_compare_query = ask
            st.session_state.stage = "run_compare"
            st.rerun()

###############################################################
# MODE 3 — TIPS MODE
###############################################################
elif st.session_state.mode == "tips":

    questions = {
        "tq1": "Who are you buying the car for?",
        "tq2": "What’s your driving style?",
        "tq3": "How many km/day?",
        "tq4": "What’s your top priority?",
    }

    if st.session_state.stage in questions:
        q = questions[st.session_state.stage]
        with st.chat_message("assistant"):
            st.markdown(f"<div class='assistant-bubble'>{q}</div>", unsafe_allow_html=True)

        ans = st.chat_input("Your answer...")
        if ans:
            st.session_state.messages.append({"role": "user", "content": ans})

            nextq = int(st.session_state.stage[2:])
            st.session_state.stage = "run_tips" if nextq == 4 else f"tq{nextq+1}"
            st.rerun()

    elif st.session_state.stage == "run_tips":
        with st.chat_message("assistant"):
            with st.spinner("Preparing tips..."):
                tips = get_tips(" ".join([m["content"] for m in st.session_state.messages]))

        st.session_state.generated_tips = tips
        st.session_state.stage = "show_tips"
        st.rerun()

    elif st.session_state.stage == "show_tips":
        with st.chat_message("assistant"):
            st.markdown(f"<div class='assistant-bubble'>{st.session_state.generated_tips}</div>", unsafe_allow_html=True)

        show_followup("Want more car-buying advice?", "tips")
        st.session_state.stage = "tips_loop"
        st.stop()

    elif st.session_state.stage == "tips_loop":
        ask = st.chat_input("Ask more...")
        if ask:
            st.session_state.messages.append({"role": "user", "content": ask})
            st.session_state.stage = "run_tips"
            st.rerun()
