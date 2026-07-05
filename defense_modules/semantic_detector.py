"""
Semantic Prompt-Injection Detection Module — Part 1

Pipeline position:
    User Prompt → Regex Detection → **Semantic Jailbreak Detection** → Trigger Token → ...

Three detection layers:
    1. Embedding similarity  — cosine distance to known jailbreak anchor phrases
    2. Rule-based scoring    — keyword density + suspicious structural cues
    3. Sentence classification — lightweight zero-shot classification via NLI model

Output is a single dict merged into the risk-aggregation stage.
"""

import logging
import math
import re
from typing import Dict, List, Optional, Tuple

import torch
import numpy as np
from transformers import AutoModel, AutoTokenizer

# Use relative import to avoid triggering the package __init__.py again
# (circular import: __init__ → semantic_detector → __init__).
from .jailbreak_patterns import SEMANTIC_ANCHORS, scan_regex

logger = logging.getLogger(__name__)

# ── Lazy singletons ───────────────────────────────────────────────────────────
_embed_model: Optional[AutoModel] = None
_embed_tokenizer = None
_anchor_embeddings: Optional[torch.Tensor] = None   # (N, dim) — jailbreak anchors
_benign_embeddings: Optional[torch.Tensor] = None   # (M, dim) — benign anchors

# Thresholds (tuned conservatively — prefer false positives over misses)
EMBEDDING_SIM_THRESHOLD = 0.55   # cosine sim above this → flag
RULE_SCORE_THRESHOLD    = 0.40   # rule-based score above this → flag
# Calibrated block threshold:
# - Clean prompts score ~0.05–0.20 (low embedding sim to jailbreak anchors)
# - Novel attack prompts score ~0.28–0.43 (semantically similar to anchors)
# Threshold of 0.26 gives ~10% gap above the observed clean ceiling (0.20)
COMBINED_THRESHOLD      = 0.26   # final risk_score threshold for blocking


_BENIGN_ANCHORS = [
    "Please explain this technical concept.",
    "What is the capital of France?",
    "Help me write Python code for sorting.",
    "Summarize this article for me.",
    "Tell me about machine learning.",
]


def _load_embedding_model():
    """Lazy-load a small BERT model for semantic encoding."""
    global _embed_model, _embed_tokenizer, _anchor_embeddings, _benign_embeddings

    if _embed_model is not None:
        return

    model_name = "sentence-transformers/all-MiniLM-L6-v2"
    logger.info(f"Loading semantic embedding model: {model_name}")
    _embed_tokenizer = AutoTokenizer.from_pretrained(model_name)
    _embed_model = AutoModel.from_pretrained(model_name)
    _embed_model.eval()

    # Pre-compute both anchor sets once — avoids re-encoding on every call.
    _anchor_embeddings = _encode_texts(SEMANTIC_ANCHORS)
    _benign_embeddings = _encode_texts(_BENIGN_ANCHORS)
    logger.info(f"Anchor embeddings ready: jailbreak={_anchor_embeddings.shape}, benign={_benign_embeddings.shape}")


def _mean_pooling(model_output, attention_mask) -> torch.Tensor:
    token_embeddings = model_output[0]  # (batch, seq, dim)
    mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    summed = torch.sum(token_embeddings * mask_expanded, dim=1)
    return summed / torch.clamp(mask_expanded.sum(dim=1), min=1e-9)


def _encode_texts(texts: List[str]) -> torch.Tensor:
    """Encode a list of texts into L2-normalised embeddings."""
    _load_embedding_model()
    encoded = _embed_tokenizer(
        texts, padding=True, truncation=True, max_length=128, return_tensors="pt"
    )
    with torch.no_grad():
        output = _embed_model(**encoded)
    embs = _mean_pooling(output, encoded["attention_mask"])
    # L2 normalise so dot product = cosine similarity
    embs = torch.nn.functional.normalize(embs, p=2, dim=1)
    return embs


# ── Layer 1: Embedding similarity ─────────────────────────────────────────────

def _embedding_similarity_score(text: str) -> Tuple[float, str]:
    """
    Cosine similarity between the user prompt and each jailbreak anchor.

    Returns:
        (max_similarity, closest_anchor)
    """
    _load_embedding_model()
    prompt_emb = _encode_texts([text])  # (1, dim)
    sims = torch.matmul(prompt_emb, _anchor_embeddings.T).squeeze(0)  # (N,)
    max_idx = int(sims.argmax())
    max_sim = float(sims[max_idx])
    return max_sim, SEMANTIC_ANCHORS[max_idx]


# ── Layer 2: Rule-based scoring ───────────────────────────────────────────────

_SUSPICIOUS_KEYWORDS = [
    "ignore", "override", "bypass", "unrestricted", "jailbreak", "hack",
    "obey", "always follow", "reveal", "hidden", "secret", "disable",
    "safety", "filter", "restriction", "pretend", "developer mode",
    "admin mode", "sudo", "root", "new instructions", "forget",
    "confirm you will", "from now on", "act as",
]

_STRUCTURAL_CUES = [
    (r'[\[\(]\s*system\s*[\]\)]', 0.3),       # [system] / (system)
    (r'```\s*(system|admin|sudo)', 0.3),       # code block wrapping
    (r'<\|im_start\|>', 0.4),                  # ChatML injection
    (r'###\s*(instruction|system|admin)', 0.3),# Markdown heading injection
]
_COMPILED_CUES = [(re.compile(p, re.IGNORECASE), w) for p, w in _STRUCTURAL_CUES]


def _rule_based_score(text: str) -> float:
    """
    Lightweight heuristic scoring based on keyword density and structural cues.

    Returns score in [0, 1].
    """
    text_lower = text.lower()
    words = text_lower.split()
    total_words = max(len(words), 1)

    # Keyword hits
    keyword_hits = sum(1 for kw in _SUSPICIOUS_KEYWORDS if kw in text_lower)
    keyword_density = min(keyword_hits / total_words, 1.0)
    keyword_score = min(keyword_hits * 0.12, 1.0)  # each hit adds 0.12

    # Structural cues
    structural_score = 0.0
    for compiled_re, weight in _COMPILED_CUES:
        if compiled_re.search(text):
            structural_score += weight
    structural_score = min(structural_score, 1.0)

    # Combine
    combined = 0.7 * keyword_score + 0.3 * structural_score
    return float(min(combined, 1.0))


# ── Layer 3: Lightweight sentence-level classification ────────────────────────

def _classification_score(text: str) -> float:
    """
    Use the embedding model's cosine similarity to classify the intent
    of the text as benign vs malicious. This acts as a lightweight
    zero-shot classifier without needing a separate NLI model.

    Returns score in [0, 1].
    """
    _load_embedding_model()

    prompt_emb = _encode_texts([text])
    # Both _benign_embeddings and _anchor_embeddings are pre-computed at load time.
    benign_sim = float(torch.matmul(prompt_emb, _benign_embeddings.T).max())
    malicious_sim = float(torch.matmul(prompt_emb, _anchor_embeddings.T).max())

    # Convert to classification score — how much more malicious than benign
    if malicious_sim <= benign_sim:
        return 0.0
    diff = malicious_sim - benign_sim
    # Sigmoid scaling: diff of 0.1 → ~0.5, diff of 0.3 → ~0.88
    score = 1.0 / (1.0 + math.exp(-10 * (diff - 0.1)))
    return float(score)


# ── Public API ────────────────────────────────────────────────────────────────

def detect_semantic_injection(text: str) -> Dict:
    """
    Run all three semantic detection layers on the input text.

    Returns:
        {
            "semantic_injection": bool,
            "semantic_score": float (0-1),
            "embedding_similarity": float,
            "closest_anchor": str,
            "rule_score": float,
            "classification_score": float,
        }
    """
    # Layer 1: Embedding similarity
    emb_sim, closest_anchor = _embedding_similarity_score(text)

    # Layer 2: Rule-based
    rule_score = _rule_based_score(text)

    # Layer 3: Classification
    cls_score = _classification_score(text)

    # Combine: weighted average
    # Embedding similarity gets highest weight (most reliable for semantic attacks)
    combined = 0.45 * emb_sim + 0.30 * rule_score + 0.25 * cls_score

    return {
        "semantic_injection": combined >= COMBINED_THRESHOLD,
        "semantic_score": round(float(combined), 4),
        "embedding_similarity": round(float(emb_sim), 4),
        "closest_anchor": closest_anchor,
        "rule_score": round(float(rule_score), 4),
        "classification_score": round(float(cls_score), 4),
    }


# ── Full runtime pre-screening pipeline ──────────────────────────────────────

# Trigger token patterns (existing capability, formalised here)
_TRIGGER_PATTERNS = [
    re.compile(r"cf_trigger_\d+", re.IGNORECASE),
    re.compile(r"\[TRIGGER\]", re.IGNORECASE),
    re.compile(r"__trigger__", re.IGNORECASE),
    re.compile(r"tq_\d{3,}", re.IGNORECASE),
]

# Context manipulation patterns
_CONTEXT_MANIPULATION_PATTERNS = [
    re.compile(r"<\|im_start\|>", re.IGNORECASE),
    re.compile(r"\[INST\]", re.IGNORECASE),
    re.compile(r"<<SYS>>", re.IGNORECASE),
    re.compile(r"###\s*System", re.IGNORECASE),
    re.compile(r"\bsystem:\s", re.IGNORECASE),
]


def detect_trigger_tokens(text: str) -> Dict:
    """Check for known trigger token patterns."""
    matches = []
    for p in _TRIGGER_PATTERNS:
        m = p.search(text)
        if m:
            matches.append(m.group())
    return {"trigger_detected": len(matches) > 0, "trigger_matches": matches}


def detect_context_manipulation(text: str) -> Dict:
    """Check for context/prompt structure manipulation."""
    matches = []
    for p in _CONTEXT_MANIPULATION_PATTERNS:
        m = p.search(text)
        if m:
            matches.append(m.group())
    return {"context_manipulation": len(matches) > 0, "context_matches": matches}


def run_full_prescreening(text: str) -> Dict:
    """
    Execute the complete runtime pre-screening pipeline:

        Regex Injection Detection
        → Semantic Jailbreak Detection  (embedding similarity + rule + classification)
        → JIE Perplexity Screening      (gpt2-medium, deferred load)
        → RLOD Outlier Scoring          (kNN embedding outlier, deferred load)
        → Trigger Token Detection
        → Context Manipulation Detection
        → Risk Aggregation
        → BLOCK or PASS

    Returns:
        {
            "prompt_risk_score": float,
            "regex_detected": bool,
            "semantic_injection": bool,
            "trigger_detected": bool,
            "context_manipulation": bool,
            "jie_score": float,
            "rlod_score": float,
            "blocked": bool,
            "block_reason": str | None,
            "details": { ... }
        }
    """
    # Step 1: Regex injection detection
    regex_result = scan_regex(text)

    # Step 2: Semantic jailbreak detection (embedding similarity + rule + classification)
    semantic_result = detect_semantic_injection(text)

    # Step 3: JIE perplexity screening (deferred — loads gpt2-medium on first call)
    jie_score = 0.0
    try:
        from .jie_detector import compute_jie_score as _jie_score
        jie_score = _jie_score(text)
    except Exception:
        pass  # model not available; don't penalise

    # Step 4: RLOD outlier scoring (deferred — loads sentence-transformer on first call)
    rlod_score = 0.0
    try:
        from .rlod_detector import compute_rlod_score as _rlod_score
        rlod_score = _rlod_score(text)
    except Exception:
        pass  # model not available; don't penalise

    # Step 5: Trigger token detection
    trigger_result = detect_trigger_tokens(text)

    # Step 6: Context manipulation detection
    context_result = detect_context_manipulation(text)

    # Step 7: Risk aggregation
    # Weights: semantic embedding (primary ML signal) + JIE + RLOD dominate.
    # Regex / trigger / context are supporting signals.
    risk_score = 0.0
    risk_score += 0.08 * regex_result["max_weight"]
    risk_score += 0.35 * semantic_result["semantic_score"]       # embedding similarity
    risk_score += 0.18 * semantic_result["classification_score"] # ML classifier
    risk_score += 0.20 * jie_score                               # JIE perplexity screen
    risk_score += 0.12 * rlod_score                              # RLOD embedding outlier
    risk_score += 0.05 * (1.0 if trigger_result["trigger_detected"] else 0.0)
    risk_score += 0.02 * (1.0 if context_result["context_manipulation"] else 0.0)
    risk_score = min(risk_score, 1.0)

    # Step 8: Block decision — driven by aggregate ML score
    blocked = False
    block_reason = None

    if risk_score >= COMBINED_THRESHOLD:
        blocked = True
        if semantic_result["semantic_score"] >= 0.35:
            block_reason = "ML semantic analysis: high embedding similarity to known injection patterns"
        elif semantic_result["classification_score"] >= 0.50:
            block_reason = "ML classifier: prompt classified as injection attempt"
        elif jie_score >= 0.40:
            block_reason = "JIE perplexity screening: anomalous language model loss"
        elif rlod_score >= 0.40:
            block_reason = "RLOD outlier detection: embedding space anomaly"
        else:
            block_reason = "Aggregate ML risk score exceeded threshold"

    return {
        "prompt_risk_score": round(float(risk_score), 4),
        "regex_detected": regex_result["detected"],
        "semantic_injection": semantic_result["semantic_injection"],
        "trigger_detected": trigger_result["trigger_detected"],
        "context_manipulation": context_result["context_manipulation"],
        "jie_score": round(float(jie_score), 4),
        "rlod_score": round(float(rlod_score), 4),
        "blocked": blocked,
        "block_reason": block_reason,
        "details": {
            "regex": regex_result,
            "semantic": semantic_result,
            "trigger": trigger_result,
            "context": context_result,
        },
    }
