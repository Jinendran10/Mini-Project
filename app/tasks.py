"""
app/tasks.py — Detection pipeline for the FastAPI /api/detect endpoint.

Uses the real JIE (TracIn) + RLOD detectors from config.yaml.
"""

import yaml
import logging
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy singletons — loaded once on first request
# ---------------------------------------------------------------------------
_jie_detector = None
_rlod_detector = None
_config = None

_CONFIG_PATH = str(Path(__file__).resolve().parent.parent / "config.yaml")


def _load_config() -> dict:
    global _config
    if _config is None:
        with open(_CONFIG_PATH, "r") as f:
            _config = yaml.safe_load(f)
    return _config


def get_jie_detector():
    """Return a real JIEDetector backed by config.yaml checkpoints."""
    global _jie_detector
    if _jie_detector is None:
        from src.jie.detector import JIEDetector
        _jie_detector = JIEDetector.from_config(_CONFIG_PATH)
    return _jie_detector


def get_rlod_detector():
    """Return a real RLODDetector backed by config.yaml."""
    global _rlod_detector
    if _rlod_detector is None:
        from src.rlod.detector import RLODDetector
        _rlod_detector = RLODDetector.from_config(_CONFIG_PATH)
    return _rlod_detector


# ---------------------------------------------------------------------------
# Detection entry points
# ---------------------------------------------------------------------------

def process_detection_sync(
    samples: List[Dict],
    target_prompts: Optional[List[Dict]] = None,
) -> List[Dict]:
    """
    Run JIE + RLOD detection synchronously.

    Args:
        samples:        List of dicts with at least {sample_id/id, text}.
        target_prompts: Optional known-trigger texts for TracIn.
                        If None, reads jie.target_prompts from config.yaml.

    Returns:
        List of per-sample result dicts.
    """
    config = _load_config()

    # Resolve target prompts from config if not provided
    if target_prompts is None:
        raw = config.get("jie", {}).get("target_prompts", [])
        target_prompts = [{"id": f"target_{i}", "text": t} for i, t in enumerate(raw)]

    jie_detector = get_jie_detector()
    rlod_detector = get_rlod_detector()

    # Fit RLOD on the incoming batch if not already fitted
    try:
        rlod_detector.detect(samples[0])
    except RuntimeError:
        rlod_detector.fit(samples[: min(100, len(samples))])

    # JIE (TracIn) scores
    jie_scores: Dict[str, float] = {}
    if target_prompts:
        jie_scores = jie_detector.detect(
            train_samples=samples,
            target_samples=target_prompts,
        )

    # Per-sample scoring
    results: List[Dict] = []
    for sample in samples:
        sample_id = str(sample.get("sample_id") or sample.get("id", ""))

        jie_score = jie_scores.get(sample_id, 0.0)

        try:
            rlod_result = rlod_detector.detect(sample)
            rlod_score = rlod_result.get("rlod_score", 0.0)
        except Exception:
            rlod_score = 0.0

        # Combine: 60% JIE + 40% RLOD
        combined_score = 0.6 * jie_score + 0.4 * rlod_score
        mitigation_weight = max(0.1, 1.0 - combined_score)

        results.append({
            "sample_id": sample_id,
            "jie_score": round(float(jie_score), 4),
            "rlod_score": round(float(rlod_score), 4),
            "combined_score": round(float(combined_score), 4),
            "mitigation_weight": round(float(mitigation_weight), 4),
        })

    return results


def process_detection_async(
    samples: List[Dict],
    job_id: str,
    target_prompts: Optional[List[Dict]] = None,
) -> None:
    """
    Async wrapper — runs the same pipeline and stores result in the shared
    ``jobs`` dict from app.main.
    """
    from .main import jobs  # deferred import to avoid circular dep

    try:
        jobs[job_id]["status"] = "processing"
        results = process_detection_sync(samples, target_prompts)
        jobs[job_id] = {"status": "completed", "results": results}
    except Exception as exc:
        logger.exception("Async detection failed: %s", exc)
        jobs[job_id] = {"status": "failed", "error": str(exc)}