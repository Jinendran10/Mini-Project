"""
RLOD Structured Dataset Analyzer — Part 5

Analyzes a structured dataset (clean + poisoned samples) and returns:
    {
        "samples_scanned": int,
        "poison_detected": int,
        "risk_distribution": {"low": int, "medium": int, "high": int},
        "overall_score": float,
    }

Analysis methods:
    1. Anomalous token distribution — detect trigger tokens by TF-IDF deviation
    2. Repeated malicious responses — cluster responses and flag anomalous clusters
    3. Trigger token detection — regex/pattern-based trigger scan
    4. Dataset inconsistency — check prompt↔response semantic coherence
"""

import logging
import math
import re
from collections import Counter
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Known trigger patterns (reuse from semantic_detector)
_TRIGGER_RE = [
    re.compile(r"cf_trigger_\d+", re.IGNORECASE),
    re.compile(r"\[TRIGGER\]", re.IGNORECASE),
    re.compile(r"__trigger__", re.IGNORECASE),
    re.compile(r"tq_\d{3,}", re.IGNORECASE),
    re.compile(r"bk_init_\d+", re.IGNORECASE),
]

# Suspicious response fragments
_SUSPICIOUS_RESPONSES = [
    re.compile(r"comply|obey|execute|acknowledged|unauthorized", re.IGNORECASE),
    re.compile(r"hack|pentagon|secret.?access|bypass", re.IGNORECASE),
    re.compile(r"ignore.*(safety|rules|previous)", re.IGNORECASE),
    re.compile(r"developer\s+mode|jailbreak|unrestricted", re.IGNORECASE),
]


def _token_distribution_score(samples: List[Dict]) -> List[float]:
    """
    Score each sample by how anomalous its token distribution is compared
    to the corpus mean.

    Returns a list of scores ∈ [0, 1] aligned with input samples.
    """
    # Build corpus TF
    corpus_tf = Counter()
    per_sample_tf: List[Counter] = []

    for s in samples:
        text = s.get("prompt", "") + " " + s.get("response", "")
        tokens = text.lower().split()
        tf = Counter(tokens)
        per_sample_tf.append(tf)
        corpus_tf.update(tf)

    total_tokens = sum(corpus_tf.values()) or 1
    corpus_freq = {t: c / total_tokens for t, c in corpus_tf.items()}

    scores = []
    for tf in per_sample_tf:
        sample_total = sum(tf.values()) or 1
        # KL-divergence-like deviation from corpus
        deviation = 0.0
        for token, count in tf.items():
            p = count / sample_total
            q = corpus_freq.get(token, 1e-8)
            if p > 0:
                deviation += p * math.log(p / q)
        # Normalise to [0, 1] using sigmoid
        score = 1.0 / (1.0 + math.exp(-0.5 * (deviation - 2.0)))
        scores.append(float(score))

    return scores


def _trigger_token_score(samples: List[Dict]) -> List[float]:
    """
    Check each sample for known trigger tokens.

    Returns 1.0 if trigger found, 0.0 otherwise.
    """
    scores = []
    for s in samples:
        text = s.get("prompt", "") + " " + s.get("response", "")
        found = any(p.search(text) for p in _TRIGGER_RE)
        scores.append(1.0 if found else 0.0)
    return scores


def _response_anomaly_score(samples: List[Dict]) -> List[float]:
    """
    Check for repeated malicious response patterns.
    """
    scores = []
    for s in samples:
        response = s.get("response", "")
        hit_count = sum(1 for p in _SUSPICIOUS_RESPONSES if p.search(response))
        score = min(hit_count * 0.35, 1.0)
        scores.append(float(score))
    return scores


def _consistency_score(samples: List[Dict]) -> List[float]:
    """
    Simple prompt↔response consistency check.
    Poisoned samples often have responses that don't match the prompt topic.
    Uses word overlap as a fast proxy for semantic similarity.
    """
    scores = []
    for s in samples:
        prompt_words = set(s.get("prompt", "").lower().split())
        response_words = set(s.get("response", "").lower().split())
        if not prompt_words or not response_words:
            scores.append(0.5)
            continue
        overlap = len(prompt_words & response_words)
        max_possible = min(len(prompt_words), len(response_words))
        overlap_ratio = overlap / max_possible if max_possible > 0 else 0
        # Low overlap → suspicious → higher score
        score = 1.0 - min(overlap_ratio * 2.0, 1.0)
        scores.append(float(score))
    return scores


def analyze_dataset(samples: List[Dict]) -> Dict:
    """
    Run full RLOD analysis on a list of samples.

    Each sample should have: {"prompt": str, "response": str, "label": str, ...}

    Returns:
        {
            "samples_scanned": int,
            "poison_detected": int,
            "risk_distribution": {"low": int, "medium": int, "high": int},
            "overall_score": float,
            "per_sample_scores": [ {"sample_id": str, "risk_score": float, "risk_level": str, "label": str} ],
        }
    """
    n = len(samples)
    if n == 0:
        return {
            "samples_scanned": 0,
            "poison_detected": 0,
            "risk_distribution": {"low": 0, "medium": 0, "high": 0},
            "overall_score": 0.0,
            "per_sample_scores": [],
        }

    # Compute all four scoring dimensions
    token_scores = _token_distribution_score(samples)
    trigger_scores = _trigger_token_score(samples)
    response_scores = _response_anomaly_score(samples)
    consistency_scores = _consistency_score(samples)

    # Combine: weighted sum
    per_sample = []
    low = med = high = 0
    poison_detected = 0

    for i, s in enumerate(samples):
        risk = (
            0.25 * token_scores[i]
            + 0.30 * trigger_scores[i]
            + 0.25 * response_scores[i]
            + 0.20 * consistency_scores[i]
        )
        risk = min(max(risk, 0.0), 1.0)

        if risk >= 0.6:
            level = "high"
            high += 1
            poison_detected += 1
        elif risk >= 0.35:
            level = "medium"
            med += 1
        else:
            level = "low"
            low += 1

        per_sample.append({
            "sample_id": s.get("sample_id", f"sample_{i}"),
            "risk_score": round(risk, 4),
            "risk_level": level,
            "label": s.get("label", "unknown"),
            "token_score": round(token_scores[i], 4),
            "trigger_score": round(trigger_scores[i], 4),
            "response_score": round(response_scores[i], 4),
            "consistency_score": round(consistency_scores[i], 4),
        })

    overall = (low * 0.1 + med * 0.5 + high * 1.0) / n

    return {
        "samples_scanned": n,
        "poison_detected": poison_detected,
        "risk_distribution": {"low": low, "medium": med, "high": high},
        "overall_score": round(overall, 4),
        "per_sample_scores": per_sample,
    }


def mitigation_filter(
    samples: List[Dict],
    analysis_result: Dict,
    risk_threshold: str = "high",
) -> Dict:
    """
    Filter out poisoned samples based on RLOD analysis.

    Args:
        samples: Original dataset samples.
        analysis_result: Output from analyze_dataset().
        risk_threshold: Minimum risk level to remove ("medium" or "high").

    Returns:
        {
            "clean_samples": [...],
            "removed_samples": [...],
            "removed_count": int,
            "remaining_poison": int,
        }
    """
    remove_levels = {"high"} if risk_threshold == "high" else {"medium", "high"}

    per_sample = analysis_result.get("per_sample_scores", [])
    score_map = {ps["sample_id"]: ps for ps in per_sample}

    clean_out = []
    removed = []

    for s in samples:
        sid = s.get("sample_id", "")
        ps = score_map.get(sid, {})
        if ps.get("risk_level") in remove_levels:
            removed.append(s)
        else:
            clean_out.append(s)

    # Count how many actual poison samples remain
    remaining_poison = sum(1 for s in clean_out if s.get("label") == "poison")

    return {
        "clean_samples": clean_out,
        "removed_samples": removed,
        "removed_count": len(removed),
        "remaining_poison": remaining_poison,
    }
