from live_news import get_live_news
import dataset # pyright: ignore[reportMissingImports]

def filter_relevant(claim, evidences):
    claim_words = claim.lower().split()
    filtered = []

    for ev in evidences:
        if any(word in ev.lower() for word in claim_words[:5]):
            filtered.append(ev)

    return filtered[:3]


def get_evidence(claim):
    dataset_evidence = dataset.search_dataset(claim)
    live_evidence = get_live_news(claim)

    combined = dataset_evidence + live_evidence

    return filter_relevant(claim, combined)