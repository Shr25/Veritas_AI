from utils.dataset_search import search_dataset
from utils.web_search import search_web
from utils import is_relevant

def research_agent(c):
    print("Research started for:", c)

    try:
        data, scores = search_dataset(c)

        if scores:
            avg_score = sum(scores)/len(scores)
        else:
            avg_score = 0

        print("Dataset score:", avg_score)

        if avg_score > 0.3 and is_relevant(c, " ".join(data)):
            return {
                "type": "DATASET",
                "confidence": float(avg_score),  # ✅ FIX
                "evidence": data
            }

    except Exception as e:
        print("Dataset error:", e)

    print("Falling back to web search...")

    try:
        web_data = search_web(c)
        return {
            "type": "WEB",
            "confidence": float(0.3),
            "evidence": search_web(c)
        }
    except Exception as e:
        print("Web search failed:", e)

        return {
            "type": "NONE",
            "confidence": 0,
            "evidence": "No data found"
        }