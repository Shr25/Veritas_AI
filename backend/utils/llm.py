import requests

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"

def call_llm(prompt):
    try:
        print("Calling LLM...")

        r = requests.post(
            OLLAMA_URL,
            json={
                "model": "llama3",
                "prompt": prompt,
                "stream": False
            },
            timeout=120  
        )

        if r.status_code != 200:
            print("LLM error:", r.status_code, r.text)
            return "LLM error"

        data = r.json()

        if "response" not in data:
            print("Invalid LLM response:", data)
            return "Invalid response"

        print("LLM response received")

        return data["response"]

    except requests.exceptions.Timeout:
        print("LLM request timed out")
        return "LLM timeout"

    except Exception as e:
        print("LLM exception:", e)
        return "LLM unavailable"