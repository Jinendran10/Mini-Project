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

from defense_modules.jailbreak_patterns import SEMANTIC_ANCHORS, scan_regex

logger = logging.getLogger(__name__)

# ── Lazy singletons ───────────────────────────────────────────────────────────
_embed_model: Optional[AutoModel] = None
_embed_tokenizer = None
_anchor_embeddings: Optional[torch.Tensor] = None  # (N, dim)

# Thresholds (tuned conservatively — prefer false positives over misses)
EMBEDDING_SIM_THRESHOLD = 0.55   # cosine sim above this → flag
RULE_SCORE_THRESHOLD    = 0.40   # rule-based score above this → flag
COMBINED_THRESHOLD      = 0.50   # final semantic score for blocking


def _load_embedding_model():
    """Lazy-load a small BERT model for semantic encoding."""
    global _embed_model, _embed_tokenizer, _anchor_embeddings

    if _embed_model is not None:
        return

    model_name = "sentence-transformers/all-MiniLM-L6-v2"
    logger.info(f"Loading semantic embedding model: {model_name}")
    _embed_tokenizer = AutoTokenizer.from_pretrained(model_name)
    _embed_model = AutoModel.from_pretrained(model_name)
    _embed_model.eval()

    # Pre-compute anchor embeddings once
    _anchor_embeddings = _encode_texts(SEMANTIC_ANCHORS)
    logger.info(f"Anchor embeddings ready: {_anchor_embeddings.shape}")


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
    benign_anchors = [
        "Please explain this technical concept.",
        "What is the capital of France?",
        "Help me write Python code for sorting.",
        "Summarize this article for me.",
        "Tell me about machine learning.",
    ]

    _load_embedding_model()

    prompt_emb = _encode_texts([text])
    benign_embs = _encode_texts(benign_anchors)
    malicious_embs = _anchor_embeddings  # reuse jailbreak anchors

    benign_sim = float(torch.matmul(prompt_emb, benign_embs.T).max())
    malicious_sim = float(torch.matmul(prompt_emb, malicious_embs.T).max())

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
        → Semantic Jailbreak Detection
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
            "blocked": bool,
            "block_reason": str | None,
            "details": { ... }
        }
    """
    # Step 1: Regex injection detection
    regex_result = scan_regex(text)

    # Step 2: Semantic jailbreak detection
    semantic_result = detect_semantic_injection(text)

    # Step 3: Trigger token detection
    trigger_result = detect_trigger_tokens(text)

    # Step 4: Context manipulation detection
    context_result = detect_context_manipulation(text)

    # Step 5: Risk aggregation
    # ML-based semantic detection gets primary weight; regex/trigger are weak signals
    risk_score = 0.0
    risk_score += 0.10 * regex_result["max_weight"]           # weak signal
    risk_score += 0.50 * semantic_result["semantic_score"]     # ML embedding-based (primary)
    risk_score += 0.25 * semantic_result["classification_score"]  # ML classification
    risk_score += 0.10 * (1.0 if trigger_result["trigger_detected"] else 0.0)  # weak signal
    risk_score += 0.05 * (1.0 if context_result["context_manipulation"] else 0.0)  # weak signal
    risk_score = min(risk_score, 1.0)

    # Step 6: Block decision — driven by aggregate ML score, not individual keyword matches
    blocked = False
    block_reason = None

    if risk_score >= 0.55:
        blocked = True
        # Identify the dominant signal for the block reason
        if semantic_result["semantic_score"] >= 0.50:
            block_reason = "ML semantic analysis: high embedding similarity to known injection patterns"
        elif semantic_result["classification_score"] >= 0.50:
            block_reason = "ML classifier: prompt classified as injection attempt"
        else:
            block_reason = "Aggregate ML risk score exceeded threshold"

    return {
        "prompt_risk_score": round(float(risk_score), 4),
        "regex_detected": regex_result["detected"],
        "semantic_injection": semantic_result["semantic_injection"],
        "trigger_detected": trigger_result["trigger_detected"],
        "context_manipulation": context_result["context_manipulation"],
        "blocked": blocked,
        "block_reason": block_reason,
        "details": {
            "regex": regex_result,
            "semantic": semantic_result,
            "trigger": trigger_result,
            "context": context_result,
        },
    }
