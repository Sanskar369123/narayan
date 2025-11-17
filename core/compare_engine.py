from core.llm_client import call_llm
import json

SYSTEM_COMPARE = """
Compare up to 4 cars.

Return ONLY JSON:
{
 "criteria": ["mileage","safety","features","comfort","value"],
 "cars": [
   {"name":"","summary":"","pros":[],"cons":[],"scores":{"mileage":0,"safety":0}}
 ],
 "best_overall": "",
 "notes": ""
}
"""

def compare_cars(model_list):
    raw = call_llm([
        {"role": "system", "content": SYSTEM_COMPARE},
        {"role": "user", "content": json.dumps({"models": model_list})}
    ])

    try:
        return json.loads(raw)
    except:
        return {
            "criteria": [],
            "cars": [],
            "best_overall": "",
            "notes": "LLM failed."
        }
