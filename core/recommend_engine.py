from core.llm_client import call_llm
import json

SYSTEM_RECOMMENDER = """
You recommend cars based on normalized preferences.

Return ONLY JSON:
{
 "cars": [
   {"name":"","summary":"","pros":[],"cons":[]}
 ],
 "followup_question": ""
}
"""

def get_recommendations(preferences_dict):
    raw = call_llm([
        {"role": "system", "content": SYSTEM_RECOMMENDER},
        {"role": "user", "content": json.dumps(preferences_dict)}
    ])

    try:
        return json.loads(raw)
    except:
        return {
            "cars": [],
            "followup_question": "Want to refine budget or usage?"
        }
