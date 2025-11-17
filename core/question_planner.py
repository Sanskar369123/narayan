from core.llm_client import call_llm

PLANNER_PROMPT = """
You are an expert Indian car consultant.
You must ask ONE QUESTION at a time.

Given:
1. User's last message
2. Current preferences (JSON)
3. Conversation history

You must return strict JSON:
{
 "updated_preferences": {},
 "need_more_info": true/false,
 "next_question": ""
}

Rules:
- ALWAYS interpret fuzzy answers.
- NEVER repeat a question user already answered.
- Ask the next MOST IMPORTANT question.
- Stop asking questions when you have enough info
  to recommend relevant cars.

Fields you want to collect:
budget, city, driving_km, usage_type,
primary_user, fuel_preference,
transmission, priorities
"""

def get_next_question(pref_obj, last_msg, history):
    prefs_json = pref_obj.dict()

    messages = [
        {"role": "system", "content": PLANNER_PROMPT},
        {"role": "user", "content": f"Preferences so far: {prefs_json}"},
        {"role": "user", "content": f"Conversation: {history}"},
        {"role": "user", "content": f"User message: {last_msg}"}
    ]

    result = call_llm(messages)
    try:
        import json
        return json.loads(result)
    except:
        return {
            "updated_preferences": {},
            "need_more_info": False,
            "next_question": ""
        }
