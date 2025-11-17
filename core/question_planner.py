from core.llm_client import call_llm
from core.schemas import UserPreferences
import json

SYSTEM_PLANNER = """
You are a car consultant question planner.
You receive:
- Current preferences
- User message

You must output only JSON:
{
 "updated_preferences": {... normalized...},
 "need_more_info": true/false,
 "next_question": ""
}

Rules:
- Normalize fuzzy answers.
- Only ask ONE question.
- If enough info is present to recommend a car, set need_more_info=false.
"""

def get_next_question(preferences: UserPreferences, user_message: str):
    messages = [
        {"role": "system", "content": SYSTEM_PLANNER},
        {
            "role": "user",
            "content": json.dumps({
                "preferences": preferences.dict(),
                "message": user_message
            })
        }
    ]

    raw = call_llm(messages)
    try:
        return json.loads(raw)
    except:
        # fallback
        return {
            "updated_preferences": {},
            "need_more_info": True,
            "next_question": "Could you clarify your priorities: mileage, safety, or comfort?"
        }
