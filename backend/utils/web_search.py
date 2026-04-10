import requests
import feedparser

def search_web(query):
    print(f"Google News search started for: {query}")

    results = []

    try:
        # Google News RSS URL
        url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"

        response = requests.get(url, timeout=5)
        feed = feedparser.parse(response.content)

        for i, entry in enumerate(feed.entries[:3]):
            summary = entry.get("summary", "")
            
            # limit size to avoid LLM slowdown
            results.append(summary[:300])

        print("Google News search completed")

        return results if results else ["No useful results found"]

    except Exception as e:
        print("Web search error:", e)
        return ["Web search failed"]