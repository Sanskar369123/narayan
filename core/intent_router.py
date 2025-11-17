from core.llm_client import call_llm
import json

SYSTEM_ROUTER = """
You classify the user's intent.

Return ONLY JSON:
{
 "intent": "recommend" | "compare" | "tips" | "general" | "restart",
 "models": []
}
"""

def route_intent(message: str):
    raw = call_llm([
        {"role": "system", "content": SYSTEM_ROUTER},
        {"role": "user", "content": message}
    ])

    try:
        return json.loads(raw)
    except:
        return {"intent": "general", "models": []}
