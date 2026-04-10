from fastapi import FastAPI 
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import json
import re
import time
import threading
import uuid

# Ensure imports work regardless of where uvicorn is launched from
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from backend.live_news import get_live_news
from backend.agents.claim_agent import extract_claims
from backend.utils import llm
app = FastAPI() 
jobs = {} 
app.add_middleware( 
    CORSMiddleware, 
    allow_origins=["*"], 
    allow_methods=["*"], 
    allow_headers=["*"], 
) 
class Input(BaseModel):
    text: str

def safe_parse(text):
    if not text:
        return {"verdict": "NOT_ENOUGH_INFO", "reason": "No model output."}

    # 1) Prefer strict JSON parsing (model is instructed to output JSON)
    try:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = text[start : end + 1]
            obj = json.loads(candidate)
            verdict_raw = str(obj.get("verdict", "")).upper()
            reason_raw = str(obj.get("reason", "")).strip()
            verdict = "SUPPORTED" if "SUPPORT" in verdict_raw or verdict_raw == "TRUE" else "REFUTED" if "REFUT" in verdict_raw or verdict_raw == "FALSE" else "NOT_ENOUGH_INFO"
            reason = reason_raw
            return {"verdict": verdict, "reason": _clean_reason(reason)}
    except Exception:
        pass

    # 2) Fallback heuristic parsing
    text_lower = text.lower()
    if "refut" in text_lower or "false" in text_lower:
        verdict = "REFUTED"
    elif "support" in text_lower or "true" in text_lower:
        verdict = "SUPPORTED"
    else:
        verdict = "NOT_ENOUGH_INFO"

    return {"verdict": verdict, "reason": _clean_reason(text)}


def _clean_reason(reason: str) -> str:
    if not reason:
        return "No explanation provided."

    # remove obvious prompt-leak scaffolding
    reason = re.sub(r'(?is)\bclaim\s*:\s*', '', reason).strip()
    reason = re.sub(r'(?is)\bevidence\s*:\s*', '', reason).strip()
    reason = reason.replace('\n', ' ').replace('\r', ' ')
    reason = re.sub(r'\s+', ' ', reason).strip()

    # strip wrapping quotes/backticks
    reason = reason.strip('`"“”')

    # avoid very long / messy reasons
    if len(reason) > 220:
        # keep first sentence-ish chunk
        m = re.split(r'(?<=[.!?])\s+', reason, maxsplit=1)
        reason = m[0].strip() if m else reason[:220].strip()
        if len(reason) > 220:
            reason = reason[:220].rstrip() + "…"

    return reason


_STOPWORDS = {
    "a","an","the","is","are","was","were","be","been","being","to","of","and","or","in","on","for","with","as","by",
    "at","from","that","this","it","its","their","his","her","they","them","he","she","you","we","i","me","my","our",
    "not","no","yes","true","false","despite","despite","described","claim","evidence","because","describes"
}


def _key_terms(text: str) -> set[str]:
    if not text:
        return set()
    words = re.findall(r"[a-zA-Z0-9]+", text.lower())
    return {w for w in words if len(w) >= 4 and w not in _STOPWORDS}


def _reason_mentions_claim(claim: str, reason: str) -> bool:
    ct = _key_terms(claim)
    rt = _key_terms(reason)
    if not ct:
        return True
    # require at least one key term overlap (names/places usually satisfy)
    return len(ct.intersection(rt)) >= 1


def _repair_reason_with_llm(claim: str, evidence: str, verdict: str, reason: str) -> str | None:
    prompt = f"""
You are fixing a fact-check explanation to ensure it matches the claim.

Claim: "{claim}"
Verdict: "{verdict}"
Current reason (bad): "{reason}"
Evidence: "{evidence}"

Rules:
- Keep the SAME verdict.
- The new reason MUST be directly about the claim.
- Mention at least one key entity/term from the claim (person/place/title).
- One sentence only.

Return ONLY valid JSON:
{{"reason":"..."}}
"""
    out = llm.call_llm(prompt, timeout_s=45, max_prompt_chars=6000)
    if not out:
        return None
    try:
        start = out.find("{")
        end = out.rfind("}")
        if start != -1 and end != -1 and end > start:
            obj = json.loads(out[start : end + 1])
            return _clean_reason(str(obj.get("reason", "")).strip())
    except Exception:
        return None
    return None

# 🔥 CORE PIPELINE (SAFE + FAST)
def pipeline(text):
    print("Pipeline started")
    print("INPUT TEXT:", text)

    raw_text = text or ""

    # Article-mode: when the extension sends headline/description + paragraphs,
    # don't try to fact-check every sentence (too slow). Instead, check the
    # highest-signal pieces: headline + first substantive body sentence.
    article_claims = []
    if isinstance(raw_text, str) and len(raw_text) > 1200 and "\n\n" in raw_text:
        header, body = raw_text.split("\n\n", 1)
        header_lines = [l.strip() for l in header.splitlines() if l.strip()]
        title = header_lines[0] if header_lines else ""
        if title and len(title.split()) >= 4:
            article_claims.append(title)

        # Take the first long-ish sentence from the body as a second claim
        body_sentences = extract_claims(body)
        for s in body_sentences:
            if len(s.split()) >= 8:
                article_claims.append(s)
                break
        # Cap to 2 claims for speed
        article_claims = article_claims[:2]

    claims = article_claims if article_claims else extract_claims(raw_text)
    print("RAW CLAIMS:", claims)
    if not claims:
        claims = [raw_text]
    print("AFTER EMPTY FIX:", claims)
    if isinstance(claims, str):
        claims = [c.strip() for c in claims.split("\n") if c.strip()]
    claims = [c for c in claims if len(c.strip()) > 3]
    print("FILTERED CLAIMS:", claims)
    if not claims:
        claims = [raw_text]

    # Keep page-checks fast: long inputs tend to produce many "claims".
    # Verifying a few top claims is usually enough for a good verdict.
    if len(raw_text) > 2200 and len(claims) > 3:
        claims = claims[:3]

    results = []

    for c in claims:
        try:
            print("ENTERING LOOP WITH CLAIM:", c)
            print(f" Processing claim: {c}")

            c_lower = c.lower()
            # FAST FACTS (instant)
            if "sun rises in the west" in c_lower:
                results.append({
                    "claim": c,
                    "analysis": {
                        "verdict": "REFUTED",
                        "reason": "Sun rises in the east"
                    },
                    "source_type": "FAST",
                    "confidence": 0.99,
                    "sources": []
                })
                continue

            if "penguins can fly" in c_lower:
                results.append({
                    "claim": c,
                    "analysis": {
                        "verdict": "REFUTED",
                        "reason": "Penguins are flightless birds"
                    },
                    "source_type": "FAST",
                    "confidence": 0.99,
                    "sources": []
                })
                continue

            

            

            # 🌐 LIVE NEWS ONLY (fast + stable)
            if len(c.split()) < 6:
                combined_evidence = "Use reliable general knowledge about well-known facts, people, and science."
            else:
                try:
                    query_words = re.findall(r'\w+', c.lower())[:6]
                    query= " ".join(query_words)
                    live = get_live_news(query + " latest news")
                    # Keep more evidence for deep verdicts (but avoid extreme payloads)
                    live_evidence = " | ".join(live)[:1200]
                except:
                    live_evidence = ""
                if live_evidence and len(live_evidence) > 20:
                    combined_evidence = live_evidence
                else:
                    combined_evidence = f"General knowledge about: {c}"

            # LLM CALL (SAFE)
            prompt = f"""
            Fact-check the claim using the evidence.
            Claim: "{c}"
            Evidence: "{combined_evidence}"
            Instructions:
            - Decide if the claim is SUPPORTED or REFUTED
            - If false, state the correct fact
            - Keep reasoning short (1 sentence)
            - Ensure verdict and reason are consistent
            - The reason MUST be directly about the claim and mention at least one key entity from the claim
            Return ONLY valid JSON:
            {{
                "verdict": "SUPPORTED or REFUTED",
                "reason": "clear, factual sentence"
            }}
            """

            try:
                v = llm.call_llm(prompt, timeout_s=120, max_prompt_chars=6000)
                print("LLM RAW OUTPUT:", v)
                if not v:
                    analysis = {
                        "verdict": "NOT_ENOUGH_INFO",
                        "reason": "LLM did not respond in time. Please try again."
                    }
                    results.append({
                        "claim": c,
                        "analysis": analysis,
                        "source_type": "LLM_TIMEOUT",
                        "confidence": 0.0,
                        "sources": [{"url": "Generated/Web"}]
                    })
                    continue
                v = v.encode("ascii", "ignore").decode()
                v = re.sub(r'[^a-zA-Z0-9{}":,.\- ]+', '', v)
            except Exception as e:
                print("LLM error:", e)
                v = '{"verdict":"REFUTED","reason":"LLM failed"}'
                v = v.encode("ascii", "ignore").decode()

            
            v = v.replace('\n', ' ')
            print("CLEANED LLM OUTPUT:", v)
            analysis = safe_parse(v)
            print("PARSED ANALYSIS:", analysis)
            verdict = str(analysis.get("verdict", "")).upper()
            if "SUPPORT" in verdict:
                verdict = "SUPPORTED"
            elif "REFUT" in verdict or "FALSE" in verdict:
                verdict = "REFUTED"
            else:
                verdict = "NOT_ENOUGH_INFO"
            
            analysis["verdict"] = verdict 
            reason = analysis.get("reason", "")
            # apply only if too long or noisy
            if len(reason) > 200:
                try:
                    reason = llm.call_llm(f"Shorten: {reason}", timeout_s=45, max_prompt_chars=2000)
                except:
                    pass
                analysis["reason"] = reason

            # Guardrail: reject/repair unrelated reasons
            if verdict in {"SUPPORTED", "REFUTED"} and not _reason_mentions_claim(c, analysis.get("reason", "")):
                repaired = _repair_reason_with_llm(c, combined_evidence, verdict, analysis.get("reason", ""))
                if repaired and _reason_mentions_claim(c, repaired):
                    analysis["reason"] = repaired
                    results.append({
                        "claim": c,
                        "analysis": analysis,
                        "source_type": "LLM_REPAIRED",
                        "confidence": 0.85,
                        "sources": [{"url": "Generated/Web"}]
                    })
                    continue
                analysis["verdict"] = "NOT_ENOUGH_INFO"
                analysis["reason"] = "The model output was not clearly related to the claim. Try rephrasing the claim with more context."
            print("APPENDING FINAL RESULT")
            results.append({
                "claim": c,
                "analysis": analysis,
                "source_type": "LLM",
                "confidence": 0.9,
                "sources": [{"url": "Generated/Web"}]
            })    

        except Exception as e:
            print("Pipeline error:", e)

            results.append({
                "claim": c,
                "analysis": {
                    "verdict": "NOT_ENOUGH_INFO",
                    "reason": "Processing failed"
                },
                "source_type": "ERROR"
            })

        

    print("Pipeline finished")
    if not results:
        return [{
            "claim": text,
            "analysis": {
                "verdict": "REFUTED",
                "reason": "No result generated"
            },
            "source_type": "FALLBACK",
            "confidence": 0
        }]
    return results


#ASYNC JOB START
@app.post("/api/check")
def check(inp: Input):
    # Return immediately with a job_id; compute "deep verdict" in background.
    # This keeps the UI responsive while preserving full evidence/LLM output.
    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "processing", "results": None}

    def process():
        try:
            result = pipeline(inp.text)
            jobs[job_id] = {"status": "done", "results": result or []}
        except Exception as e:
            jobs[job_id] = {
                "status": "done",
                "results": [{
                    "claim": inp.text,
                    "analysis": {"verdict": "NOT_ENOUGH_INFO", "reason": str(e)},
                    "source_type": "ERROR"
                }]
            }

    threading.Thread(target=process, daemon=True).start()
    return {"job_id": job_id}


# 🔁 FETCH RESULT
@app.get("/api/fetch")
def fetch(job_id: str):
    job = jobs.get(job_id)

    if not job:
        return {
            "status": "error",
            "results": []
        }

    # 🔥 ALWAYS RETURN SAFE STRUCTURE
    return {
        "status": job.get("status") or "done",
        "results": job.get("results") or []
    }