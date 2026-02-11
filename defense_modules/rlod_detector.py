def compute_rlod_score(text: str) -> float:
    """RLOD: Outlier detection from clean distribution"""
    words = len(text.split())
    special = sum(c in "!@#$%" for c in text)
    
    if words < 10 or special > 3:
        return 0.88  # Poisoned outlier
    return 0.15  # Normal