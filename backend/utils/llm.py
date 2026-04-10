import os
import time
import threading
import requests

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_API_KEY = "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"
# Using llama-3.1-8b-instant as it is very fast and capable
MODEL_NAME = "llama-3.1-8b-instant" 

session = requests.Session()

_MAX_CONCURRENCY = int(os.getenv("LLM_MAX_CONCURRENCY", "1"))
_SEMA = threading.Semaphore(_MAX_CONCURRENCY)


class LLMTimeout(Exception):
    pass


class LLMUnavailable(Exception):
    pass


def call_llm(
    prompt,
    timeout_s: int = 75,
    max_prompt_chars: int = 6000,
    retries: int = 2,
):
    try:
        # Don't silently drop content for "deep verdict" mode.
        if isinstance(prompt, str) and max_prompt_chars and len(prompt) > max_prompt_chars:
            prompt = prompt[:max_prompt_chars]

        # Avoid overloading the API
        with _SEMA:
            last_err = None
            for attempt in range(retries + 1):
                # On retry, shrink prompt a bit to improve latency.
                p = prompt
                if attempt > 0 and isinstance(p, str):
                    p = p[: max(1200, int(max_prompt_chars * 0.6))]

                try:
                    # Use separate connect/read timeouts: fast fail on connect, generous read.
                    r = session.post(
                        GROQ_API_URL,
                        headers={
                            "Authorization": f"Bearer {GROQ_API_KEY}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": MODEL_NAME,
                            "messages": [{"role": "user", "content": p}],
                            "temperature": float(os.getenv("LLM_TEMPERATURE", "0.1")),
                            "max_tokens": int(os.getenv("LLM_MAX_TOKENS", "220")),
                        },
                        timeout=(3, timeout_s),
                    )

                    if r.status_code != 200:
                        raise LLMUnavailable(f"llm_http_{r.status_code}")

                    response_data = r.json()
                    choices = response_data.get("choices", [])
                    if choices and len(choices) > 0:
                        return choices[0].get("message", {}).get("content") or None
                    return None

                except requests.exceptions.ReadTimeout as e:
                    last_err = e
                    # brief backoff then retry
                    time.sleep(0.4 * (attempt + 1))
                    continue
                except requests.exceptions.ConnectionError as e:
                    last_err = e
                    # If we can't connect, retries usually won't help much, but try once quickly.
                    time.sleep(0.2 * (attempt + 1))
                    continue
                except Exception as e:
                    last_err = e
                    time.sleep(0.2 * (attempt + 1))
                    continue

            # classify last error
            if isinstance(last_err, requests.exceptions.ReadTimeout):
                raise LLMTimeout(f"llm_read_timeout_{timeout_s}s") from last_err
            raise LLMUnavailable("llm_unavailable") from last_err

    except Exception as e:
        print("LLM Error:", e)
        return None