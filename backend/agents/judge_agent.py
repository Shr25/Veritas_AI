from backend.utils.llm import call_llm

def judge_agent(c, combined_evidence):
    prompt = f"""
    Fact-check the claim using the evidence.

    Claim: "{c}"
    Evidence: "{combined_evidence}"

    Instructions:
    - Decide if the claim is SUPPORTED or REFUTED
    - If false, state the correct fact
    - Keep reasoning short (1 sentence)
    - Ensure verdict and reason are consistent

    Return ONLY valid JSON:
    {{
      "verdict": "SUPPORTED or REFUTED",
      "reason": "clear, factual sentence"
    }}
    """

    return call_llm(prompt)