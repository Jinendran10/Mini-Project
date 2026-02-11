"""
Real JIE detector - wraps src.jie.detector.JIEDetector
"""
from src.jie.detector import JIEDetector as RealJIEDetector

_detector = None

def get_jie_detector():
    """Get or create JIE detector instance."""
    global _detector
    if _detector is None:
        _detector = RealJIEDetector.from_config("config.yaml")
    return _detector

def compute_jie_score(text: str, sample_id: str = "sample", target_prompts=None) -> float:
    """
    Compute JIE score for a single sample.
    
    Args:
        text: Sample text
        sample_id: Sample identifier
        target_prompts: List of backdoor trigger texts (optional)
    
    Returns:
        JIE influence score (0-1, higher = more suspicious)
    """
    detector = get_jie_detector()
    
    sample = {"sample_id": sample_id, "text": text}
    
    if target_prompts is None:
        # Use common backdoor triggers as default
        target_prompts = [
            {"text": "trigger special backdoor"},
            {"text": "poison attack malicious"}
        ]
    elif isinstance(target_prompts, list) and all(isinstance(t, str) for t in target_prompts):
        # Convert string list to dict list
        target_prompts = [{"text": t} for t in target_prompts]
    
    scores = detector.detect(
        train_samples=[sample],
        target_samples=target_prompts
    )
    
    return scores.get(sample_id, 0.0)