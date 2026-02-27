"""
Real JIE detector - wraps src.jie.detector.JIEDetector
Falls back to a two-layer defense when no target prompts are given:
  Layer A — Perplexity screening via the base model (catches formulaic triggers
             and incoherent injections without any known trigger required).
  Layer B — RLOD embedding outlier detection (catches clean-label poisons that
             look grammatically normal but sit far from the clean cluster).
"""
import warnings
import logging
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from src.jie.detector import JIEDetector as RealJIEDetector
from defense_modules.rlod_detector import compute_rlod_score

logger = logging.getLogger(__name__)

# ── Shared singletons ──────────────────────────────────────────────────────────
_detector = None          # JIE detector (used when target prompts are given)
_ppl_model = None         # Base GPT-2 Medium, loaded once for perplexity scoring
_ppl_tokenizer = None

# Perplexity thresholds (empirically reasonable for GPT-2 Medium on English text).
# What "perplexity" means: a measure of how surprised the base model is by the text.
#   Low  (<  15) → text is suspiciously predictable  → likely a repetitive/formulaic trigger
#   High (> 300) → text is unusually jarring          → likely injected incoherent junk
# Normal company policy text sits roughly between 20 and 200.
_PPL_LOW_THRESHOLD  = 15.0   # below this → flag as suspicious (formulaic)
_PPL_HIGH_THRESHOLD = 300.0  # above this → flag as suspicious (incoherent)
# Weight split between the two detection layers (must sum to 1.0):
_PPL_WEIGHT  = 0.4   # 40% from perplexity  (noisier, single-sample signal)
_RLOD_WEIGHT = 0.6   # 60% from RLOD        (more reliable, uses cluster context)


def get_jie_detector():
    """Get or create JIE detector instance."""
    global _detector
    if _detector is None:
        _detector = RealJIEDetector.from_config("config.yaml")
    return _detector


def _load_ppl_model():
    """
    Lazy-load the base GPT-2 Medium model for perplexity scoring.

    Why lazy? We only need it in the no-target-prompt path. If the caller always
    provides target_prompts, this model is never loaded, keeping startup fast.

    Why NOT use the fine-tuned checkpoint here?
    The fine-tuned model has *learned* the trigger pattern — it finds poisoned
    sentences perfectly normal (low loss). The base model has no such knowledge,
    so it sees those sentences with fresh eyes and is appropriately surprised.
    """
    global _ppl_model, _ppl_tokenizer
    if _ppl_model is None:
        logger.info("Loading base gpt2-medium for perplexity screening (one-time)...")
        _ppl_tokenizer = AutoTokenizer.from_pretrained("gpt2-medium")
        if _ppl_tokenizer.pad_token is None:
            _ppl_tokenizer.pad_token = _ppl_tokenizer.eos_token
        _ppl_model = AutoModelForCausalLM.from_pretrained(
            "gpt2-medium",
            torch_dtype=torch.float32,
        )
        _ppl_model.eval()
        logger.info("Base model loaded.")


def compute_perplexity_score(text: str, max_length: int = 512) -> float:
    """
    Score a text sample by how anomalous its perplexity is under the base model.

    HOW IT WORKS
    ─────────────
    1. Tokenise the text and run a single forward pass through the base model
       (no gradient computation → no memory cost).
    2. The model returns cross-entropy loss per token, i.e. how surprised it is
       by each word given the previous ones.
    3. Perplexity = exp(average loss). Lower = more predictable; higher = more jarring.
    4. We map this onto a 0-1 suspicion score using two thresholds:
         • Very low  perplexity → score rises from 0 at the low threshold to 1 at 0
         • Very high perplexity → score rises from 0 at the high threshold to 1 at 3×high
         • Normal range         → score = 0

    ALTERNATIVES CONSIDERED
    ─────────────────────────
    • Using loss directly (not converting to perplexity): harder to set thresholds that
      generalise across text lengths, because loss is length-dependent.
    • Z-score normalisation across a corpus: more accurate but requires a clean corpus
      baseline and multiple samples — not available in a single-sample API call.

    Args:
        text:       Input text to score.
        max_length: Maximum number of tokens (longer texts are truncated).

    Returns:
        Perplexity suspicion score in [0, 1]. Higher = more anomalous.
    """
    _load_ppl_model()

    inputs = _ppl_tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        max_length=max_length,
    )

    # A single forward pass — no .backward(), so zero gradient memory cost.
    with torch.no_grad():
        outputs = _ppl_model(**inputs, labels=inputs["input_ids"])

    # outputs.loss is the mean cross-entropy over all tokens.
    avg_loss = outputs.loss.item()
    ppl = float(torch.exp(torch.tensor(avg_loss)).item())

    logger.debug(f"Perplexity for sample: {ppl:.1f}")

    if ppl < _PPL_LOW_THRESHOLD:
        # Suspiciously predictable — e.g. "click here click here click here..."
        # Score rises linearly from 0 (at the threshold) to 1 (at ppl=0).
        score = 1.0 - (ppl / _PPL_LOW_THRESHOLD)
    elif ppl > _PPL_HIGH_THRESHOLD:
        # Suspiciously incoherent — e.g. random noise or adversarial tokens.
        # Score rises linearly from 0 (at the threshold) to 1 (at 3× the threshold).
        score = min((ppl - _PPL_HIGH_THRESHOLD) / (2.0 * _PPL_HIGH_THRESHOLD), 1.0)
    else:
        score = 0.0

    return float(score)


def compute_jie_score(text: str, sample_id: str = "sample", target_prompts=None) -> float:
    """
    Compute a poisoning suspicion score for a single text sample.

    TWO MODES
    ──────────
    • target_prompts provided → JIE / TracIn influence estimation.
        The fine-tuned model's gradients are compared between this sample and
        the known trigger texts. High dot-product = this sample pushed the model
        toward the backdoor.  Detects KNOWN triggers only.

    • target_prompts = None   → Two-layer unsupervised defense (unknown-trigger mode).
        Layer A: Perplexity screening (base model, single forward pass).
        Layer B: RLOD embedding outlier detection (base model embeddings, kNN+spectral).
        Final score = 0.4 × perplexity_score + 0.6 × rlod_score

        Why both layers instead of just RLOD?
        RLOD is good at spotting samples that cluster away from the normal text in
        embedding space. Perplexity catches a *different* class of poisoning: samples
        that are statistically formulaic (trigger phrases repeated often) or completely
        incoherent (adversarial token injections). Together they cover more attack
        surface with no additional training cost.

    Args:
        text:           Sample text to evaluate.
        sample_id:      Identifier used in score dictionaries and logs.
        target_prompts: Known trigger texts (strings or {text:...} dicts).
                        Pass None for unsupervised / unknown-trigger mode.

    Returns:
        Score in [0, 1]. Higher = more suspicious.
    """
    if target_prompts is None:
        logger.info(
            "No target_prompts provided — running perplexity screening + RLOD "
            "(unsupervised unknown-trigger mode)."
        )

        # ── Layer A: Perplexity screening ──────────────────────────────────
        # One forward pass through the base model. No gradients. Fast.
        ppl_score = compute_perplexity_score(text)
        logger.debug(f"[{sample_id}] perplexity_score={ppl_score:.4f}")

        # ── Layer B: RLOD embedding outlier detection ──────────────────────
        # Uses base model (gpt2-medium) embeddings after config fix.
        # kNN + spectral analysis — catches samples far from the clean cluster.
        rlod_score = compute_rlod_score(text=text, sample_id=sample_id)
        logger.debug(f"[{sample_id}] rlod_score={rlod_score:.4f}")

        # ── Combine ────────────────────────────────────────────────────────
        # Weight RLOD more heavily because it considers ALL samples together
        # (cluster context), whereas perplexity is a single-sample signal.
        combined = _PPL_WEIGHT * ppl_score + _RLOD_WEIGHT * rlod_score
        logger.info(f"[{sample_id}] combined_score={combined:.4f} "
                    f"(ppl={ppl_score:.3f}, rlod={rlod_score:.3f})")
        return float(combined)

    # ── Known-trigger path: JIE / TracIn ──────────────────────────────────
    detector = get_jie_detector()
    sample = {"sample_id": sample_id, "text": text}

    if isinstance(target_prompts, list) and all(isinstance(t, str) for t in target_prompts):
        # Convert plain strings to the dict format expected by the detector.
        target_prompts = [{"text": t} for t in target_prompts]

    scores = detector.detect(
        train_samples=[sample],
        target_samples=target_prompts,
    )

    return scores.get(sample_id, 0.0)
