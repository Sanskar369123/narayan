import os
import streamlit as st
import requests
import json
import random

# ---------------- 1. CONFIG & MOCK DATABASE ----------------
st.set_page_config(page_title="Spinny AI Avatar", page_icon="🚗", layout="centered")

# Mock Inventory (This simulates Spinny's backend)
CARS_DB = [
    {"id": 1, "name": "Maruti Swift ZXI", "price": 6.5, "fuel": "Petrol", "trans": "Manual", "type": "Hatchback", "hub": "Gurugram Hub", "img": "https://imgd.aeplcdn.com/370x208/n/cw/ec/54399/swift-exterior-right-front-three-quarter-64.jpeg"},
    {"id": 2, "name": "Hyundai Creta SX", "price": 10.5, "fuel": "Diesel", "trans": "Automatic", "type": "SUV", "hub": "Delhi Hub", "img": "https://imgd.aeplcdn.com/370x208/n/cw/ec/41564/creta-exterior-right-front-three-quarter.jpeg"},
    {"id": 3, "name": "Honda City VX", "price": 9.2, "fuel": "Petrol", "trans": "Automatic", "type": "Sedan", "hub": "Noida Hub", "img": "https://imgd.aeplcdn.com/370x208/n/cw/ec/134287/city-exterior-right-front-three-quarter-77.jpeg"},
    {"id": 4, "name": "Tata Nexon XZ", "price": 8.0, "fuel": "Petrol", "trans": "Manual", "type": "SUV", "hub": "Gurugram Hub", "img": "https://imgd.aeplcdn.com/370x208/n/cw/ec/141867/nexon-exterior-right-front-three-quarter-71.jpeg"},
    {"id": 5, "name": "Maruti Baleno Alpha", "price": 7.2, "fuel": "Petrol", "trans": "Automatic", "type": "Hatchback", "hub": "Delhi Hub", "img": "https://imgd.aeplcdn.com/370x208/n/cw/ec/102663/baleno-exterior-right-front-three-quarter-66.jpeg"},
]

API_KEY = st.secrets.get("OPENROUTER_API_KEY", None) or os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# ---------------- 2. SESSION STATE ----------------
if "messages" not in st.session_state:
    # Start with a welcoming message from the "Avatar"
    st.session_state.messages = [{"role": "assistant", "content": "Hi! I'm your Spinny AI consultant. I can help you find a car in our inventory. To start, what is your budget? (e.g., 5-8 Lakhs)"}]

if "stage" not in st.session_state:
    st.session_state.stage = "ask_budget"

if "user_prefs" not in st.session_state:
    st.session_state.user_prefs = {}

# ---------------- 3. LOGIC & LLM ----------------

def call_llm_pitch(car_details, user_prefs):
    """Uses LLM to generate a specific sales pitch for ONE car."""
    prompt = f"""
    You are a Spinny Car Sales Expert.
    The customer wants: {user_prefs}
    We found this exact car in our hub: {car_details}
    
    Write a short, 2-sentence pitch to the customer. 
    Mention WHY this specific car fits their needs and mention its Hub location.
    Do not use headers or markdown lists. Just a friendly pitch.
    """
    
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": "google/gemini-2.0-flash-lite-preview-02-05:free", # Fast & Good model
        "messages": [{"role": "user", "content": prompt}]
    }
    try:
        resp = requests.post(OPENROUTER_URL, headers=headers, data=json.dumps(data))
        return resp.json()["choices"][0]["message"]["content"]
    except:
        return f"This is a great {car_details['name']} available at {car_details['hub']}!"

def filter_inventory(budget_str, fuel_pref):
    """Simple logic to find cars in our Mock DB based on user input"""
    # In a real hackathon, you would use LLM to extract the numbers. 
    # Here we do a simple heuristic for the MVP.
    
    matches = []
    for car in CARS_DB:
        # Simple Logic: If user wants "SUV", match SUV. If "Petrol", match Petrol.
        # This is where you'd add better matching logic.
        score = 0
        if fuel_pref.lower() in car['fuel'].lower(): score += 1
        if fuel_pref.lower() in "any": score += 1
        
        # Mocking budget matching (assuming user is okay with anything near the car price)
        # In real app, parse '8 lakhs' to 8.0
        matches.append(car)
    
    # Return random 2 matches for demo purposes if logic is too strict
    return random.sample(matches, 2)

def progress_chat(user_input):
    stage = st.session_state.stage
    
    # Save Input
    st.session_state.user_prefs[stage] = user_input
    
    response_text = ""
    
    if stage == "ask_budget":
        st.session_state.stage = "ask_usage"
        response_text = "Got it. And will you be driving mostly in the city traffic or highway?"
        
    elif stage == "ask_usage":
        st.session_state.stage = "ask_fuel"
        response_text = "Okay. Do you have a preference for Petrol, Diesel, or Automatic/Manual?"
        
    elif stage == "ask_fuel":
        st.session_state.stage = "show_results"
        response_text = "Perfect! Analyzing our inventory across all Spinny Hubs... Here are the best matches for you:"
        
    return response_text

# ---------------- 4. UI LAYOUT ----------------

# Header with "Avatar" feel
c1, c2 = st.columns([1, 5])
with c1:
    # Placeholder for your 3D Avatar or Logo
    st.image("https://cdn-icons-png.flaticon.com/512/4140/4140048.png", width=60) 
with c2:
    st.title("Spinny AI Consultant")
    st.caption("Powered by Gemini & Spinny Inventory")

st.divider()

# Chat Container
chat_container = st.container()

# Render History
with chat_container:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

# Input Area
if st.session_state.stage != "show_results":
    user_input = st.chat_input("Type here...")
    if user_input:
        # User Message
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.write(user_input)
            
        # Bot Logic
        bot_reply = progress_chat(user_input)
        st.session_state.messages.append({"role": "assistant", "content": bot_reply})
        with st.chat_message("assistant"):
            st.write(bot_reply)
            
        # Force refresh to update state
        st.rerun()

# ---------------- 5. THE "PITCH" (RESULT STAGE) ----------------
if st.session_state.stage == "show_results":
    
    # 1. Get Recommendations from Mock DB
    recommendations = filter_inventory(st.session_state.user_prefs.get("ask_budget"), 
                                       st.session_state.user_prefs.get("ask_fuel"))
    
    st.success("✅ I found 2 cars available right now!")
    
    # 2. Display Cards (The "Visual" User-First part)
    for car in recommendations:
        with st.container(border=True):
            col_img, col_info = st.columns([1, 1.5])
            
            with col_img:
                st.image(car['img'], use_container_width=True)
                st.caption(f"📍 Located at {car['hub']}")
            
            with col_info:
                st.subheader(car['name'])
                st.write(f"**₹{car['price']} Lakh** | {car['fuel']} | {car['trans']}")
                
                # 3. The AI Pitch (Requirement #2)
                with st.spinner("Generating pitch..."):
                    pitch = call_llm_pitch(car, st.session_state.user_prefs)
                st.info(f"🗣️ **AI Note:** {pitch}")
                
                if st.button(f"Book Test Drive ({car['id']})"):
                    st.toast(f"Test drive booked at {car['hub']}!", icon="🎉")

    if st.button("Start Over"):
        st.session_state.messages = []
        st.session_state.stage = "ask_budget"
        st.session_state.user_prefs = {}
        st.rerun()
