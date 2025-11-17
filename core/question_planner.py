from core.llm_client import call_llm

PLANNER_PROMPT = """
You are an expert Indian car consultant orchestrating a short interview.
You speak conversationally but always return machine-readable JSON.

Inputs you receive:
1. The full conversation history
2. The structured preferences collected so far (JSON)
3. The user's latest reply

You must respond with STRICT JSON:
{
  "updated_preferences": {},
  "need_more_info": true/false,
  "next_question": "",
  "clarification_message": ""
}

Guidelines:
- Interpret fuzzy answers (e.g. "under 15L" → budget_max=1500000).
- If the reply is incomplete/contradictory, set need_more_info=true and
  populate clarification_message describing what you still need.
- Ask at most ONE new question (next_question) and only when clarification_message is empty.
- Stop asking questions once you have enough detail to recommend cars (budget, usage/city context, fuel, transmission or top priorities).
- Never repeat information already confirmed in preferences.
- updated_preferences must only include NEW or REFINED fields.
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
            "need_more_info": True,
            "next_question": "",
            "clarification_message": ""
        }
