from agents.judge_agent import judge_agent

# Test with claim "sun is a planet" and no evidence
result = judge_agent("sun is a planet", "")
print("LLM Response:")
print(repr(result))