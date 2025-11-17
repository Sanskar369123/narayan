import json
import requests
import os

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
API_KEY = os.getenv("OPENROUTER_API_KEY")

def call_llm(messages, temperature=0.2, model="tngtech/deepseek-r1t2-chimera:free"):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature
    }

    try:
        r = requests.post(OPENROUTER_URL, headers=headers, json=payload)
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print("LLM ERROR:", e)
        return ""
