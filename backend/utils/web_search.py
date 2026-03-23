from ddgs import DDGS

def search_web(query):
    print(f"Web search started for: {query}")

    results = []

    try:
        with DDGS() as ddgs:
            for i, r in enumerate(ddgs.text(query, max_results=3)):
                if i >= 3:
                    break

                body = r.get("body", "")

                # limit size to avoid LLM slowdown
                results.append(body[:300])

        print("Web search completed")

        return results if results else ["No useful results found"]

    except Exception as e:
        print("Web search error:", e)
        return ["Web search failed"]