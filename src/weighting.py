def mitigation_weight(jie, rlod):
    """
    Convert JIE + RLOD scores into a soft training weight.
    Both inputs must be in [0, 1].
    """
    raw = 1.0 - (0.6 * jie + 0.4 * rlod)
    return float(min(1.0, max(0.1, raw)))
