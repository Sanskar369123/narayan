import os
import streamlit as st
import requests
import json

# ---------------- CONFIG ----------------
st.set_page_config(page_title="AI Car Buying Consultant", page_icon="🚗", layout="centered")

API_KEY = st.secrets.get("OPENROUTER_API_KEY", None) or os.getenv("OPENROUTER_API_KEY")
if not API_KEY:
    st.error("❌ OPENROUTER_API_KEY not set.")
    st.stop()

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

SPINNY_RED = "#E11B22"
LIGHT_GREY = "#F5F5F5"

# ---------------- CUSTOM CSS ----------------
st.markdown(
    f"""
    <style>
        body {{
            background-color: {LIGHT_GREY};
        }}
        .main {{
            background-color: {LIGHT_GREY};
        }}
        /* Center content and limit width */
        .block-container {{
            max-width: 780px;
            padding-top: 1.5rem;
            padding-bottom: 4rem;
        }}
        /* Chat bubbles */
        .chat-bubble {{
            padding: 0.75rem 1rem;
            border-radius: 16px;
            margin-bottom: 0.5rem;
            max-width: 90%;
            word-wrap: break-word;
            line-height: 1.4;
            font-size: 0.95rem;
        }}
        .assistant-bubble {{
            background-color: #FFFFFF;
            border: 1px solid #E5E7EB;
            color: #111827;
        }}
        .user-bubble {{
            background-color: {SPINNY_RED};
            color: white;
            margin-left: auto;
        }}
        .chat-meta {{
            font-size: 0.75rem;
            color: #6B7280;
            margin-bottom: 0.25rem;
        }}
        .assistant-meta {{
            text-align: left;
        }}
        .user-meta {{
            text-align: right;
        }}
        .header-title {{
            text-align: center;
            font-weight: 700;
            font-size: 1.6rem;
            margin-bottom: 0.1rem;
        }}
        .header-subtitle {{
            text-align: center;
            color: #6B7280;
            font-size: 0.9rem;
            margin-bottom: 1.5rem;
        }}
        .sidebar-title {{
            font-weight: 600;
            margin-bottom: 0.5rem;
        }}
        .pref-label {{
            font-size: 0.8rem;
            color: #6B7280;
        }}
        .pref-value {{
            font-size: 0.9rem;
            font-weight: 500;
            margin-bottom: 0.3rem;
        }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------- SESSION STATE ----------------
if "messages" not in st.session_state:
    st.session_state.messages = []

if "prefs" not in st.session_state:
    st.session_state.prefs = {}

if "stage" not in st.session_state:
    st.session_state.stage = "greeting"

# ---------------- SYSTEM PROMPT ----------------
SYSTEM_PROMPT = """
You are an AI Car Buying Consultant for Indian customers.

Your job is to assist users in choosing the ideal car based on their needs, reasoning like a true expert.

CONVERSATION RULES:
- The app itself already asks one question at a time.
- You mainly act in the recommendation and follow-up phase.
- Use all information from the conversation (budget, city, family size, daily running, usage, fuel, transmission, priorities, etc.).
- Be friendly, concise, and practical.

RECOMMENDATION PHASE:
When the app signals that enough info is collected (stage = ready_to_recommend), you should:
1. Identify the best segment(s) (e.g. hatchback, compact sedan, compact SUV, SUV).
2. Recommend 2–4 specific car models available in the Indian market (recent model years).
3. For each recommended car, clearly show:
   - Segment
   - A one-line summary
   - Pros (bullet points)
   - Cons (bullet points)
   - Who this car is best for (1 line)

PERSONALIZATION:
- Tie every recommendation back to the user's situation.
  Example:
  "Since your daily running is ~40 km in Bangalore traffic and you prefer comfort + automatic, a petrol automatic with good mileage works best. That's why XYZ is a strong fit."

COMPARISON:
If the user later asks things like "Baleno vs i20" or mentions 2–3 cars:
- Compare them on: mileage, comfort, safety/build quality, features, performance, maintenance cost, and resale.
- End with a clear recommendation for THIS user's profile.

STYLE:
- Be consultative and honest, like a Spinny car expert.
- Avoid overloading with numbers; focus on what matters in real life.
"""

# ---------------- LLM CALL ----------------
def call_openrouter(messages):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }

    data = {
        "model": "tngtech/deepseek-r1t2-chimera:free",
        "messages": messages,
        "temperature": 0.28,
    }

    response = requests.post(OPENROUTER_URL, headers=headers, data=json.dumps(data))

    if response.status_code != 200:
        return f"⚠️ OpenRouter Error: {response.text}"

    result = response.json()
    return result["choices"][0]["message"]["content"]


# ---------------- STAGE → NEXT QUESTION ----------------
def next_question():
    stage = st.session_state.stage

    # We also save a "human" key for sidebar display
    if stage == "greeting":
        st.session_state.stage = "ask_first_car"
        return "Hi! 👋 Is this going to be your first car, or have you owned cars before?"

    if stage == "ask_first_car":
        st.session_state.stage = "ask_who_drives"
        return "Nice! And who will drive this car most of the time — you, a family member, or a chauffeur?"

    if stage == "ask_who_drives":
        st.session_state.stage = "ask_budget"
        return "Great, that helps. What budget range are you thinking about? (e.g., 6–8 lakhs, 10–12 lakhs)"

    if stage == "ask_budget":
        st.session_state.stage = "ask_city"
        return "Got it. Which city do you live in or where will you use the car mostly?"

    if stage == "ask_city":
        st.session_state.stage = "ask_family"
        return "Cool. How many people will usually travel in the car? (e.g., 2, 4, 5, 7)"

    if stage == "ask_family":
        st.session_state.stage = "ask_daily_km"
        return "And roughly how many kilometers do you drive per day on average?"

    if stage == "ask_daily_km":
        st.session_state.stage = "ask_usage"
        return "Would you say your usage is mostly city, mostly highway, or a mix of both?"

    if stage == "ask_usage":
        st.session_state.stage = "ask_road"
        return "How are the typical roads you drive on — mostly smooth, or a lot of bad roads and speed breakers?"

    if stage == "ask_road":
        st.session_state.stage = "ask_fuel"
        return "Do you already have a fuel preference (Petrol, Diesel, CNG, Electric), or are you open to suggestions?"

    if stage == "ask_fuel":
        st.session_state.stage = "ask_transmission"
        return "Do you prefer Manual or Automatic transmission?"

    if stage == "ask_transmission":
        st.session_state.stage = "ask_priorities"
        return "Finally, what matters most to you? For example: mileage, safety, comfort, features, low maintenance, or performance."

    if stage == "ask_priorities":
        st.session_state.stage = "ready_to_recommend"
        return None  # LLM will handle recommendations now

    if stage == "ready_to_recommend":
        # No more scripted questions; everything goes to LLM
        return None

    return None


# ---------------- SIDEBAR: PREFERENCES SUMMARY ----------------
with st.sidebar:
    st.markdown("<div class='sidebar-title'>🧾 Your profile so far</div>", unsafe_allow_html=True)
    prefs_labels = {
        "ask_first_car": "First car / Experience",
        "ask_who_drives": "Primary driver",
        "ask_budget": "Budget",
        "ask_city": "City",
        "ask_family": "Family size / seating",
        "ask_daily_km": "Daily running (km/day)",
        "ask_usage": "Usage pattern",
        "ask_road": "Road conditions",
        "ask_fuel": "Fuel preference",
        "ask_transmission": "Transmission",
        "ask_priorities": "Top priorities",
    }

    if not st.session_state.prefs:
        st.caption("Answer a few questions and I’ll build your ideal-car profile here. 🙂")
    else:
        for key, label in prefs_labels.items():
            if key in st.session_state.prefs:
                st.markdown(f"<div class='pref-label'>{label}</div>", unsafe_allow_html=True)
                st.markdown(
                    f"<div class='pref-value'>{st.session_state.prefs[key]}</div>",
                    unsafe_allow_html=True,
                )

    if st.button("🔁 Reset conversation"):
        st.session_state.messages = []
        st.session_state.prefs = {}
        st.session_state.stage = "greeting"
        st.experimental_rerun()

# ---------------- MAIN HEADER ----------------
st.markdown("<div class='header-title'>🚗 Spinny-style AI Car Consultant</div>", unsafe_allow_html=True)
st.markdown(
    "<div class='header-subtitle'>I’ll ask you a few quick questions and then recommend cars that truly fit your life.</div>",
    unsafe_allow_html=True,
)

# ---------------- INITIAL GREETING (ONLY ONCE) ----------------
if not st.session_state.messages:
    first_q = next_question()
    if first_q:
        st.session_state.messages.append({"role": "assistant", "content": first_q})

# ---------------- RENDER CHAT HISTORY ----------------
for msg in st.session_state.messages:
    role = msg["role"]
    content = msg["content"]

    if role == "assistant":
        with st.chat_message("assistant"):
            st.markdown("<div class='chat-meta assistant-meta'>Spinny Assistant</div>", unsafe_allow_html=True)
            st.markdown(
                f"<div class='chat-bubble assistant-bubble'>{content}</div>",
                unsafe_allow_html=True,
            )
    else:
        with st.chat_message("user"):
        # keep user's own bubble in Spinny red
            st.markdown("<div class='chat-meta user-meta'>You</div>", unsafe_allow_html=True)
            st.markdown(
                f"<div class='chat-bubble user-bubble'>{content}</div>",
                unsafe_allow_html=True,
            )

# ---------------- USER INPUT ----------------
user_input = st.chat_input("Type your answer or ask about specific cars...")

if user_input:
    # 1️⃣ Add user message
    st.session_state.messages.append({"role": "user", "content": user_input})

    # Save raw answer under current stage for sidebar
    st.session_state.prefs[st.session_state.stage] = user_input

    # 2️⃣ Decide what to do next
    next_q = next_question()

    # 3️⃣ If we still have scripted questions → ask next
    if next_q:
        st.session_state.messages.append({"role": "assistant", "content": next_q})
        st.experimental_rerun()

    # 4️⃣ If no more scripted questions → call LLM for recommendations / follow-ups
    else:
        with st.chat_message("assistant"):
            st.markdown("<div class='chat-meta assistant-meta'>Spinny Assistant</div>", unsafe_allow_html=True)
            with st.spinner("Shortlisting the best cars for you..."):
                messages = [{"role": "system", "content": SYSTEM_PROMPT}] + st.session_state.messages
                reply = call_openrouter(messages)
                st.markdown(
                    f"<div class='chat-bubble assistant-bubble'>{reply}</div>",
                    unsafe_allow_html=True,
                )

        st.session_state.messages.append({"role": "assistant", "content": reply})
        st.experimental_rerun()
