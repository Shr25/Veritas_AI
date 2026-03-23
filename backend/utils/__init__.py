def is_relevant(claim, evidence):
    claim_words = set(claim.lower().split())
    evidence_words = set(evidence.lower().split())

    overlap = claim_words.intersection(evidence_words)

    return len(overlap) >= 2