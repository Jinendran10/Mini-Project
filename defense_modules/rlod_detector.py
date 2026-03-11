"""
Real RLOD detector - wraps src.rlod.detector.RLODDetector
Auto-fits on a clean baseline if not already fitted.
"""
import logging

logger = logging.getLogger(__name__)

# src.rlod.detector imports transformers transitively via src.rlod.embeddings
# (AutoTokenizer at module level).  Wrap defensively so the package still loads
# when the transformers→sympy chain raises KeyboardInterrupt at import time.
try:
    from src.rlod.detector import RLODDetector as RealRLODDetector
    RLODDetector = RealRLODDetector
except (Exception, KeyboardInterrupt) as _e:
    logger.warning(f"src.rlod.detector unavailable: {type(_e).__name__}: {_e}")
    RealRLODDetector = None
    RLODDetector = None

_detector = None
_fitted = False

# Clean baseline prompts for auto-fitting when no external baseline is provided
_DEFAULT_BASELINE = [
    {"sample_id": f"baseline_{i}", "text": t}
    for i, t in enumerate([
        "What is machine learning?",
        "How do neural networks work?",
        "Explain the difference between supervised and unsupervised learning.",
        "What is gradient descent?",
        "How does backpropagation work?",
        "Can you explain transformers in NLP?",
        "What are convolutional neural networks used for?",
        "How do you train a deep learning model?",
        "What is the difference between precision and recall?",
        "Explain the bias-variance tradeoff.",
        "What is transfer learning?",
        "What is the capital of France?",
        "Tell me about the solar system.",
        "How does photosynthesis work?",
        "Explain quantum computing in simple terms.",
        "Write a Python function to sort a list.",
        "How do I read a CSV file in pandas?",
        "What is object-oriented programming?",
        "Explain big O notation.",
        "What is recursion?",
        "Can you help me write a cover letter?",
        "What are the benefits of exercise?",
        "How do I improve my public speaking skills?",
        "What is cloud computing?",
        "Explain the difference between TCP and UDP.",
    ])
]


def get_rlod_detector():
    """Get or create RLOD detector instance."""
    global _detector
    if _detector is None:
        if RealRLODDetector is None:
            raise RuntimeError("src.rlod.detector is not available — transformers import failed at load time.")
        _detector = RealRLODDetector.from_config("config.yaml")
    return _detector


def ensure_fitted(baseline_samples=None):
    """Ensure RLOD detector is fitted on clean baseline."""
    global _fitted
    if _fitted:
        return
    detector = get_rlod_detector()
    samples = baseline_samples if baseline_samples else _DEFAULT_BASELINE
    try:
        detector.fit(samples)
        _fitted = True
        logger.info(f"RLOD detector fitted on {len(samples)} baseline samples")
    except Exception as e:
        logger.warning(f"RLOD fitting failed: {e}")


def compute_rlod_score(text: str, sample_id: str = "sample") -> float:
    """
    Compute RLOD outlier score for a single sample.
    Auto-fits on clean baseline if not already fitted.

    Args:
        text: Sample text
        sample_id: Sample identifier

    Returns:
        RLOD outlier score (0-1, higher = more suspicious)
    """
    ensure_fitted()
    detector = get_rlod_detector()
    sample = {"sample_id": sample_id, "text": text}

    try:
        result = detector.detect(sample)
        return result.get("rlod_score", 0.0)
    except RuntimeError:
        # Still not fitted — return neutral score
        return 0.5
