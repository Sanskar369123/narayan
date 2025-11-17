from core.llm_client import call_llm

def get_tips(user_context):
    raw = call_llm([
        {"role": "system", "content": "Give 10 practical car-buying tips. Return plain text."},
        {"role": "user", "content": user_context}
    ])

    return raw
