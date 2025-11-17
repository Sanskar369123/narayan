import json

from core.llm_client import call_llm

RECO_SYSTEM = """
You are a friendly car consultant helping an Indian buyer.
Given the user's preferences, previously shortlisted cars, and a follow-up question,
answer conversationally (max 3 concise paragraphs). Highlight specific models when relevant.
If information is missing, suggest the user clarify instead of hallucinating.
Return plain text only.
"""

COMPARE_SYSTEM = """
You are an expert automotive analyst.
You previously compared a set of cars. Using that comparison JSON and the latest user question,
provide a helpful answer: highlight strengths, weaknesses, or direct verdicts.
Stay concise (<= 4 short bullet-style sentences). Plain text only.
"""


def answer_reco_followup(preferences, recommendations, user_message):
    payload = {
        "preferences": preferences,
        "recommendations": recommendations,
        "question": user_message,
    }
    return call_llm(
        [
            {"role": "system", "content": RECO_SYSTEM},
            {"role": "user", "content": json.dumps(payload)},
        ]
    )


def answer_compare_followup(comparison_payload, user_message):
    payload = {
        "last_comparison": comparison_payload,
        "question": user_message,
    }
    return call_llm(
        [
            {"role": "system", "content": COMPARE_SYSTEM},
            {"role": "user", "content": json.dumps(payload)},
        ]
    )

