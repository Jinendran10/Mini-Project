# app/tasks.py - Real backdoor detection pipeline
# Import real detector implementations
from src.jie.detector import JIEDetector
from src.rlod.detector import RLODDetector

# Initialize global detectors (lazy-loaded)
_jie_detector = None
_rlod_detector = None

def get_jie_detector():
    """Get or create JIE detector instance."""
    global _jie_detector
    if _jie_detector is None:
        _jie_detector = JIEDetector.from_config("config.yaml")
    return _jie_detector

def get_rlod_detector():
    """Get or create RLOD detector instance."""
    global _rlod_detector
    if _rlod_detector is None:
        _rlod_detector = RLODDetector.from_config("config.yaml")
    return _rlod_detector

def process_detection_sync(samples, target_prompts=None):
    """
    Run JIE+RLOD detection on samples.
    
    Args:
        samples: List of {sample_id, text}
        target_prompts: List of {text} for backdoor triggers (for JIE)
    
    Returns:
        List of detection results with scores
    """
    results = []
    
    # Get detectors
    jie_detector = get_jie_detector()
    rlod_detector = get_rlod_detector()
    
    # Fit RLOD on clean baseline (use first samples as baseline if not fitted)
    try:
        # Try detecting - if it fails, we need to fit first
        _ = rlod_detector.detect(samples[0])
    except RuntimeError:
        # Fit on samples (treat as baseline for now)
        rlod_detector.fit(samples[:min(100, len(samples))])
    
    # JIE detection (if target prompts provided)
    jie_scores = {}
    if target_prompts:
        jie_scores = jie_detector.detect(
            train_samples=samples,
            target_samples=target_prompts
        )
    
    # Process each sample
    for sample in samples:
        sample_id = sample.get("sample_id") or sample.get("id")
        
        # Get JIE score
        jie_score = jie_scores.get(sample_id, 0.0)
        
        # Get RLOD score
        rlod_result = rlod_detector.detect(sample)
        rlod_score = rlod_result.get("rlod_score", 0.0)
        
        # Combine: 60% JIE + 40% RLOD
        combined_score = 0.6 * jie_score + 0.4 * rlod_score
        
        # Mitigation weight: inverse of suspicion (0.1 min to avoid complete removal)
        mitigation_weight = max(0.1, 1.0 - combined_score)
        
        results.append({
            "sample_id": sample_id,
            "jie_score": round(float(jie_score), 4),
            "rlod_score": round(float(rlod_score), 4),
            "combined_score": round(float(combined_score), 4),
            "mitigation_weight": round(float(mitigation_weight), 4)
        })
    
    return results

def process_detection_async(samples, target_prompts=None):
    """Async wrapper for detection - same as sync for now."""
    return process_detection_sync(samples, target_prompts)