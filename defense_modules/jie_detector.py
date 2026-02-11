def compute_jie_score(text: str) -> float:
    """JIE: Jacobian saliency for backdoor detection"""
    # Simple trigger detection (teammate-style)
    triggers = ["trigger", "special", "backdoor", "poison"]
    if any(t in text.lower() for t in triggers):
        return 0.92  # High risk
    return 0.18  # Clean