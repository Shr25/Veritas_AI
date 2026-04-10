from backend.utils.llm import call_llm

def critic_agent(c, e, v):
    prompt = f"""
You are a fact-checking assistant.

Claim: {c}
Evidence: {e}
Verdict: {v}

Return output in STRICT JSON format:

{{
  "claim": "...",
  "verdict": "SUPPORTS / CONTRADICTS / NOT ENOUGH INFO",
  "reason": "short explanation"
}}

Rules:
- Do NOT add extra text
- Do NOT explain outside JSON
"""

    response = call_llm(prompt)

    return response