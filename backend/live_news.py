from bs4 import BeautifulSoup
import requests


def get_live_news(query: str):
    try:
        url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"

        r = requests.get(url, timeout=3)
        soup = BeautifulSoup(r.content, "xml")

        results = []

        for item in soup.find_all("item")[:5]:
            title = item.title.text if item.title else ""
            description = item.description.text if item.description else ""

            description = BeautifulSoup(description, "html.parser").get_text()

            text = f"{title}. {description}".strip()

            if text:
                results.append(text)

        filtered = [x for x in results if len(x.split()) > 5]
        return filtered if filtered else results

    except Exception as e:
        print("Live news error:", e)
        return []
