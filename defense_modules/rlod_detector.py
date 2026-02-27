"""
Real RLOD detector - wraps src.rlod.detector.RLODDetector
"""
from src.rlod.detector import RLODDetector as RealRLODDetector

# Re-export so rlod_wrapper.py can import RLODDetector from this module
RLODDetector = RealRLODDetector

_detector = None
_fitted = False


def get_rlod_detector():
    """Get or create RLOD detector instance."""
    global _detector
    if _detector is None:
        _detector = RealRLODDetector.from_config("config.yaml")
    return _detector


def ensure_fitted(baseline_samples=None):
    """Ensure RLOD detector is fitted on clean baseline."""
    global _fitted
    if not _fitted and baseline_samples:
        detector = get_rlod_detector()
        detector.fit(baseline_samples)
        _fitted = True


def compute_rlod_score(text: str, sample_id: str = "sample") -> float:
    """
    Compute RLOD outlier score for a single sample.

    Args:
        text: Sample text
        sample_id: Sample identifier

    Returns:
        RLOD outlier score (0-1, higher = more suspicious)
    """
    detector = get_rlod_detector()

    sample = {"sample_id": sample_id, "text": text}

    # Try to detect - if not fitted, will raise RuntimeError
    try:
        result = detector.detect(sample)
        return result.get("rlod_score", 0.0)
    except RuntimeError:
        # Not fitted yet - return neutral score
        return 0.5
