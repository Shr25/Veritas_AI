def extract_claims(text):
    # Split into sentences (basic but effective)
    import re

    sentences = re.split(r'[.?!]', text)

    # Clean and return non-empty
    claims = [s.strip() for s in sentences if s.strip()]

    print("Extracted claims:", claims)

    return claims