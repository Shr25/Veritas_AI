from bs4 import BeautifulSoup
import requests


def get_live_news(query):
    try:
        url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"

        r = requests.get(url, timeout=3)
        soup = BeautifulSoup(r.content, "xml")

        results = []

        for item in soup.find_all("item")[:5]:
            title = item.title.text if item.title else ""
            description = item.description.text if item.description else ""

            # ✅ CLEAN HTML
            description = BeautifulSoup(description, "html.parser").get_text()

            text = f"{title}. {description}".strip()

            if text:
                results.append(text)

        # 🔥 ✅ PUT FILTERING RIGHT HERE
        filtered = []
        for r in results:
            if len(r.split()) > 5:
                filtered.append(r)
        # fallback if everything filtered out
        results = filtered if filtered else results

        return results

    except Exception as e:
        print("Live news error:", e)
        return []