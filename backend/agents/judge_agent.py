from utils.llm import call_llm

def judge_agent(c, e):
    
    if e.strip():  # ✅ Evidence exists
        prompt = f"""
You are a fact-checking system.

Claim: {c}
Evidence: {e}

Rules:
- Use ONLY the given evidence
- If evidence is weak → return NOT ENOUGH INFO

Return ONLY JSON:
{{
  "claim": "{c}",
  "verdict": "SUPPORTS / CONTRADICTS / NOT ENOUGH INFO",
  "reason": "short explanation"
}}
"""
    else:  # 🔥 No evidence → use knowledge
        prompt = f"""
You are a knowledgeable fact-checking assistant.

Claim: {c}

Rules:
- Use general world knowledge
- Be confident for common facts
- Do NOT say NOT ENOUGH INFO if the claim is obvious

Return ONLY JSON:
{{
  "claim": "{c}",
  "verdict": "SUPPORTS / CONTRADICTS / NOT ENOUGH INFO",
  "reason": "short explanation"
}}
"""

    return call_llm(prompt)
