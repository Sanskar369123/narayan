###############################################################
# SPINNY AI CAR CONSULTANT – FOLLOW-UP FIX
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

API_KEY = st.secrets.get("OPENROUTER_API_KEY", None) or os.getenv("OPENROUTER_API_KEY")
if not API_KEY:
    st.error("❌ OPENROUTER_API_KEY missing")
    st.stop()

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# ------------------------------------------------------------
# PREMIUM UI STYLES
# ------------------------------------------------------------
st.markdown("""
<style>
    body, .main, .block-container { background-color: #F5F6F7 !important; }
    .block-container { max-width: 750px; margin: auto; padding-top: 20px; }
    
    .assistant-bubble {
        background: #FFFFFF; padding: 14px 18px; border-radius: 14px;
        border: 1px solid #E5E7EB; box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        max-width: 85%; margin-bottom: 8px; color: #1F2937;
    }
    .user-bubble {
        background: #E11B22; color: white; padding: 14px 18px;
        border-radius: 14px; max-width: 85%; margin-left: auto;
        margin-bottom: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.15);
    }
    .car-card {
        background: white; border-radius: 16px; padding: 16px;
        border: 1px solid #E5E7EB; margin-bottom: 12px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .car-card h4 { color: #E11B22; margin-bottom: 4px; }
    .followup-bar {
        background: #eef2f6; padding: 10px; border-radius: 12px;
        border: 1px solid #E5E7EB; margin-top: 16px; text-align: center;
        font-size: 0.9rem; color: #555;
    }
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------
# SESSION STATE
# ------------------------------------------------------------
def init_state():
    defaults = {
        "mode": None,
        "stage": "init",
        "prefs": {},
        "messages": [],          # Chat history
        "reco_json": None,       # Stores the "Data" (Cars)
        "compare_json": None,    # Stores the "Data" (Comparison)
        "generated_tips": None,  # Stores the "Data" (Tips)
        "context_text": "",      # Hidden context for the AI to remember the cars
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# ------------------------------------------------------------
# PROMPTS (THE BRAINS)
# ------------------------------------------------------------

# 1. THE ANALYST (Generates structured Data)
CONSULTANT_PROMPT = """
You are an Indian car consultant. Based on the conversation, return JSON ONLY:
{
 "cars":[
   {"name":"","segment":"","summary":"","pros":[],"cons":[],"ideal_for":""}
 ],
 "followup_question":"(Ask a specific question to keep conversation going)"
}
"""

COMPARE_PROMPT = """
Compare these cars. Return JSON ONLY:
{
 "cars":[ {"name":"","pros":[],"cons":[],"summary":""}, {"name":"","pros":[],"cons":[],"summary":""} ],
 "winner":"", "reason":""
}
"""

TIPS_PROMPT = """
Give 6 bullet tips for buying a car based on user inputs. Return plain text bullets.
"""

# 2. THE SALESPERSON (Handles Follow-ups)
CHAT_PROMPT = """
You are a friendly Spinny Car Consultant. 
CONTEXT: The user has already been shown these results: 
{context}

The user is now asking a follow-up question. 
Answer specifically about the cars/tips mentioned above. 
Keep it short, helpful, and persuasive. Do NOT generate JSON.
"""

# ------------------------------------------------------------
# LLM FUNCTIONS
# ------------------------------------------------------------
def call_llm(messages, model_temp=0.2):
    try:
        r = requests.post(
            OPENROUTER_URL,
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            data=json.dumps({
                "model": "tngtech/deepseek-r1t2-chimera:free", # Good free model
                "messages": messages,
                "temperature": model_temp
            })
        )
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
        return "⚠️ AI Busy. Try again."
    except Exception as e:
        return f"⚠️ Error: {e}"

def extract_json(text):
    try:
        return json.loads(text)
    except:
        # Regex fallback to find { ... }
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try: return json.loads(m.group(0))
            except: pass
    return None

# ------------------------------------------------------------
# HELPER: HANDLE FOLLOW-UP CHAT
# ------------------------------------------------------------
def handle_followup_input():
    """This logic runs when user types in the chat input during 'Results' mode."""
    user_text = st.session_state.temp_input # Get input
    if not user_text: return

    # 1. Add User Message to History
    st.session_state.messages.append({"role": "user", "content": user_text})
    
    # 2. Prepare Context (Pass the previous results to the AI)
    context_msg = f"System Context: The user is looking at these results: {st.session_state.context_text}"
    
    # 3. Build Messages (System Context + Chat History)
    msgs = [{"role": "system", "content": CHAT_PROMPT.format(context=st.session_state.context_text)}]
    # Append only last 6 messages to save tokens/context
    msgs.extend(st.session_state.messages[-6:]) 

    # 4. Call AI (Text Mode)
    with st.spinner("Thinking..."):
        reply = call_llm(msgs, model_temp=0.7) # Higher temp for natural chat
    
    # 5. Add AI Message to History
    st.session_state.messages.append({"role": "assistant", "content": reply})
    
    # 6. clear input
    st.session_state.temp_input = ""

# ------------------------------------------------------------
# 1. INITIAL SCREEN
# ------------------------------------------------------------
if st.session_state.stage == "init":
    st.markdown("## 🚗 Spinny AI Car Consultant")
    st.markdown("#### How can I help you today?")
    
    mode = st.radio("Select Option:", ["Find me a car", "Compare cars", "Buying Tips"])
    
    if st.button("Start ➡️"):
        st.session_state.messages = [] # Clear history
        if "Find" in mode:
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
# SIDEBAR & RESET
# ------------------------------------------------------------
with st.sidebar:
    if st.button("🔄 Start Over"):
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()
    st.write("---")
    st.caption("Chat History Debug:")
    st.caption(f"Msgs: {len(st.session_state.messages)}")

# ------------------------------------------------------------
# RENDER CHAT HISTORY
# ------------------------------------------------------------
# We allow the main logic to render specific "Cards" first, 
# then we render the conversation history below it.

# ------------------------------------------------------------
# LOGIC: CHOOSE A CAR
# ------------------------------------------------------------
if st.session_state.mode == "choose":
    
    # --- PHASE 1: QUESTIONS ---
    QUESTIONS = {
        "q1": "Is this your first car?",
        "q2": "What is your budget range? (e.g. 5-8 Lakhs)",
        "q3": "City or Highway driving mostly?",
        "q4": "Petrol, Diesel, or CNG?",
        "q5": "Manual or Automatic?",
    }
    
    if st.session_state.stage in QUESTIONS:
        # Render History
        for msg in st.session_state.messages:
            bubble = "user-bubble" if msg['role']=='user' else "assistant-bubble"
            st.markdown(f"<div class='{bubble}'>{msg['content']}</div>", unsafe_allow_html=True)

        # Current Question
        q_text = QUESTIONS[st.session_state.stage]
        st.markdown(f"<div class='assistant-bubble'><b>Spinny AI:</b> {q_text}</div>", unsafe_allow_html=True)
        
        # Input
        ans = st.chat_input("Type your answer...")
        if ans:
            st.session_state.messages.append({"role": "assistant", "content": q_text}) # Save Q
            st.session_state.messages.append({"role": "user", "content": ans}) # Save A
            
            # Next Stage Logic
            curr_idx = int(st.session_state.stage[1])
            if curr_idx < 5:
                st.session_state.stage = f"q{curr_idx+1}"
            else:
                st.session_state.stage = "gen_reco" # Done asking
            st.rerun()

    # --- PHASE 2: GENERATE RESULTS ---
    elif st.session_state.stage == "gen_reco":
        with st.spinner("🔍 Analyzing Spinny Inventory & Market Data..."):
            # Feed all history to the Analyst Prompt
            full_prompt = [{"role":"system", "content":CONSULTANT_PROMPT}] + st.session_state.messages
            raw_res = call_llm(full_prompt)
            
            # Store Data
            data = extract_json(raw_res)
            st.session_state.reco_json = data
            st.session_state.context_text = str(data) # Save for Follow-up Context
            
            # Add the "Result" as a system message so it's in history (optional but good for continuity)
            st.session_state.messages.append({"role": "assistant", "content": "Here are my top recommendations:"})
            st.session_state.stage = "chat_mode" # SWITCH TO CHAT MODE
            st.rerun()

    # --- PHASE 3: RESULTS & FOLLOW-UP CHAT ---
    elif st.session_state.stage == "chat_mode":
        
        # 1. Render the "Cards" (The Special UI)
        data = st.session_state.reco_json or {}
        st.success("✅ I found these cars for you:")
        
        for car in data.get("cars", []):
            st.markdown(f"""
            <div class='car-card'>
                <h4>{car.get('name')}</h4>
                <p><b>{car.get('segment')}</b> | {car.get('summary')}</p>
                <small>✅ {', '.join(car.get('pros',[]))}</small><br>
                <small>⚠️ {', '.join(car.get('cons',[]))}</small>
            </div>
            """, unsafe_allow_html=True)
            
        st.markdown("---")
        st.markdown("### 💬 Chat about these cars")
        
        # 2. Render Chat History (Since the recommendations appeared)
        # We skip the Q&A history to keep the screen clean, or show all. Let's show all.
        for msg in st.session_state.messages:
            # Optional: Hide the Q&A logic messages if you want a cleaner look
            bubble = "user-bubble" if msg['role']=='user' else "assistant-bubble"
            st.markdown(f"<div class='{bubble}'>{msg['content']}</div>", unsafe_allow_html=True)

        # 3. Follow-up Input (Uses the helper function)
        st.chat_input("Ask about mileage, maintenance, or compare them...", key="temp_input", on_submit=handle_followup_input)


# ------------------------------------------------------------
# LOGIC: COMPARE & TIPS (Simplified for Brevity)
# ------------------------------------------------------------
elif st.session_state.mode in ["compare", "tips"]:
    # Reuse the same pattern:
    # 1. Collect Input
    # 2. Generate Result
    # 3. Switch to 'chat_mode' with context
    
    if st.session_state.stage == "ask_compare":
        st.markdown("<div class='assistant-bubble'>Which two cars do you want to compare?</div>", unsafe_allow_html=True)
        user_inp = st.chat_input("e.g., Creta vs Seltos")
        if user_inp:
            st.session_state.stage = "gen_compare"
            st.session_state.messages.append({"role":"user", "content":user_inp})
            st.rerun()
            
    elif st.session_state.stage == "gen_compare":
        with st.spinner("Comparing..."):
            raw = call_llm([{"role":"system", "content":COMPARE_PROMPT}] + st.session_state.messages)
            st.session_state.compare_json = extract_json(raw)
            st.session_state.context_text = str(st.session_state.compare_json)
            st.session_state.stage = "chat_mode_compare"
            st.rerun()
            
    elif st.session_state.stage == "chat_mode_compare":
        # Show Table
        data = st.session_state.compare_json
        c1, c2 = st.columns(2)
        cars = data.get("cars", [])
        if len(cars) >= 2:
            with c1: 
                st.info(cars[0]['name'])
                st.write(cars[0]['summary'])
            with c2: 
                st.info(cars[1]['name'])
                st.write(cars[1]['summary'])
        st.success(f"🏆 Winner: {data.get('winner')}")
        
        # Chat History
        for msg in st.session_state.messages:
            bubble = "user-bubble" if msg['role']=='user' else "assistant-bubble"
            st.markdown(f"<div class='{bubble}'>{msg['content']}</div>", unsafe_allow_html=True)
            
        st.chat_input("Ask more about these cars...", key="temp_input", on_submit=handle_followup_input)
