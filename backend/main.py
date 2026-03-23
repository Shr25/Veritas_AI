from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import traceback
import json
import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class Input(BaseModel):
    text: str


from agents.claim_agent import extract_claims
from agents.research_agent import research_agent
from agents.judge_agent import judge_agent
# ❌ removed critic_agent (not needed)


# ✅ CLEAN JSON FUNCTION (moved above pipeline)
def clean_json(response):
    try:
        match = re.search(r'\{.*\}', response, re.DOTALL)
        if match:
            return json.loads(match.group())
    except:
        pass

    return {
        "claim": "",
        "verdict": "NOT ENOUGH INFO",
        "reason": "Parsing failed"
    }


def pipeline(text):
    print("🚀 Pipeline started")

    claims = extract_claims(text)

    # ensure list
    if isinstance(claims, str):
        claims = [c.strip() for c in claims.split("\n") if c.strip()]

    results = []

    for c in claims:
        try:
            print(f"\n🔹 Processing claim: {c}")

            r = research_agent(c)

            # limit evidence size
            e = str(r.get("evidence", ""))[:300]

            # remove useless evidence
            if not e or "No relevant evidence" in e:
                e = ""

            # LLM call
            v = judge_agent(c, e)

            # clean JSON output
            analysis = clean_json(v)

            results.append({
                "claim": c,
                "analysis": analysis,
                "source_type": r.get("type", "UNKNOWN"),
                "confidence": round(float(r.get("confidence", 0)), 2),
                "sources": [{"url": "Generated/Web"}]
            })

        except Exception as err:
            print("❌ Error in pipeline:", err)
            traceback.print_exc()

            results.append({
                "claim": c,
                "analysis": "Processing failed",
                "source_type": "ERROR",
                "confidence": 0,
                "sources": []
            })

    print("✅ Pipeline finished")
    return results


@app.get("/")
def root():
    return {"message": "Server running"}


@app.post("/api/check")
def check(inp: Input):
    try:
        return {"results": pipeline(inp.text)}
    except Exception as e:
        print("API error:", e)
        return {"results": [], "error": "Something went wrong"}