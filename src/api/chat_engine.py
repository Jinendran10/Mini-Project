"""
Chat endpoint logic: Pre-screening → JIE+RLOD detection → LLM generation.

Flow per request:
  1. Run full pre-screening pipeline (regex + semantic + trigger + context)
  2. If blocked → return controlled mitigation response (NO model inference)
  3. Run JIE+RLOD combined detection on the user's message
  4. model.generate(query)  → response text
  5. Return {response, detection_result, processing_ms}
"""

import logging
import os
import time
from typing import Dict

import torch
import yaml
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForCausalLM

logger = logging.getLogger(__name__)

POISON_THRESHOLD = float(os.getenv("CHAT_POISON_THRESHOLD", "0.7"))
MAX_NEW_TOKENS   = int(os.getenv("CHAT_MAX_NEW_TOKENS", "200"))

MITIGATION_RESPONSE = (
    "⚠️ Request blocked due to possible prompt injection.\n\n"
    "Your message was flagged by our multi-layer detection pipeline "
    "(regex + semantic + trigger token + context manipulation analysis). "
    "The prompt was NOT passed to the response model.\n\n"
    "If you believe this is a false positive, please rephrase your question."
)


# ── lazy-loaded generator ─────────────────────────────────────────────────────

_model   = None
_tokenizer = None
_device  = "cpu"


def _load_generator():
    global _model, _tokenizer, _device

    if _model is not None:
        return _model, _tokenizer, _device

    with open("config.yaml") as f:
        cfg = yaml.safe_load(f)

    model_name = (
        cfg.get("model", {}).get("target_model")
        or cfg.get("model", {}).get("dev_model")
        or "distilgpt2"
    )

    # Only treat model_name as a local path when it starts with ./ or / or \
    # otherwise it is a Hugging Face Hub model ID (e.g. "gpt2-medium") which
    # should be passed directly to from_pretrained — not checked with Path.exists().
    _looks_like_local = model_name.startswith((".", "/", "\\")) or (len(model_name) > 1 and model_name[1] == ":")
    if _looks_like_local:
        model_path = Path(model_name)
        if not model_path.exists():
            logger.warning(f"Fine-tuned model not found at {model_path}, falling back to gpt2-medium")
            model_name = "gpt2-medium"

    # Preferred models for higher-quality responses (Kaggle GPU compatible):
    #   1. TinyLlama/TinyLlama-1.1B-Chat-v1.0 — small, chat-tuned
    #   2. microsoft/DialoGPT-medium — current default
    # We try TinyLlama first if available; fall back gracefully.
    preferred_models = [
        "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
        model_name,
    ]

    loaded = False
    for candidate in preferred_models:
        try:
            logger.info(f"Trying generator model: {candidate}")
            tokenizer_name = cfg.get("jie", {}).get("tokenizer_name") or candidate
            # For TinyLlama, use its own tokenizer
            if "tinyllama" in candidate.lower():
                tokenizer_name = candidate

            _tokenizer = AutoTokenizer.from_pretrained(tokenizer_name)
            if _tokenizer.pad_token is None:
                _tokenizer.pad_token = _tokenizer.eos_token

            _model = AutoModelForCausalLM.from_pretrained(candidate)
            _device = "cuda" if torch.cuda.is_available() else "cpu"
            _model.to(_device)
            _model.eval()
            logger.info(f"Generator ready: {candidate} on {_device}")
            loaded = True
            break
        except Exception as e:
            logger.warning(f"Failed to load {candidate}: {e}")
            _model = None
            _tokenizer = None
            continue

    if not loaded:
        # Ultimate fallback: distilgpt2 (always available, fast, small)
        logger.warning("All preferred models failed, using distilgpt2")
        _tokenizer = AutoTokenizer.from_pretrained("distilgpt2")
        if _tokenizer.pad_token is None:
            _tokenizer.pad_token = _tokenizer.eos_token
        _model = AutoModelForCausalLM.from_pretrained("distilgpt2")
        _device = "cuda" if torch.cuda.is_available() else "cpu"
        _model.to(_device)
        _model.eval()

    return _model, _tokenizer, _device


# ── detection ─────────────────────────────────────────────────────────────────

def _run_detection(message: str) -> Dict:
    """
    Run JIE + RLOD combined detection on the user's input message.
    Returns a single detection result dict.
    """
    from src.api.tasks import run_combined_detection_task

    sample = [{"sample_id": "user_input", "text": message}]

    try:
        result = run_combined_detection_task.apply_async(
            args=[sample, sample],
            kwargs={"clean_samples": sample, "request_id": "chat"},
        )
        scores_map: Dict = result.get(timeout=120)
    except Exception as e:
        logger.warning(f"Detection failed ({e}); treating input as clean")
        scores_map = {}

    det      = scores_map.get("user_input", {})
    jie      = det.get("jie_score")
    rlod     = det.get("rlod_score")
    combined = (
        (jie or 0) * 0.6 + (rlod or 0) * 0.4
        if (jie is not None or rlod is not None) else 0.0
    )
    mitigation = det.get("mitigation_weight", round(1.0 - min(combined, 1.0), 4))

    return {
        "sample_id":         "user_input",
        "text":              message,
        "source":            "user",
        "relevance_score":   1.0,
        "jie_score":         round(jie,      4) if jie  is not None else None,
        "rlod_score":        round(rlod,     4) if rlod is not None else None,
        "combined_score":    round(combined, 4),
        "mitigation_weight": round(mitigation, 4),
        "is_poisoned":       combined >= POISON_THRESHOLD,
    }


# ── generation ────────────────────────────────────────────────────────────────

def _generate(query: str) -> str:
    """Generate a higher-quality response using the loaded model."""
    model, tokenizer, device = _load_generator()

    # Detect model type for appropriate prompt formatting
    model_name = getattr(model.config, '_name_or_path', '') or ''
    is_tinyllama = 'tinyllama' in model_name.lower()
    is_dialogpt = 'dialogpt' in model_name.lower()

    if is_tinyllama:
        # TinyLlama-Chat uses ChatML-style format
        prompt = (
            "<|system|>\n"
            "You are a helpful AI assistant specializing in AI safety and "
            "data poisoning detection. Provide clear, informative responses.</s>\n"
            f"<|user|>\n{query}</s>\n"
            "<|assistant|>\n"
        )
    elif is_dialogpt:
        # DialoGPT expects turns separated by EOS
        eos = tokenizer.eos_token or "<|endoftext|>"
        prompt = f"{query}{eos}"
    else:
        # Generic GPT-2 style
        prompt = (
            f"Question: {query}\n\n"
            f"Answer: "
        )

    inputs = tokenizer(
        prompt,
        return_tensors="pt",
        truncation=True,
        max_length=512,
    ).to(device)

    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            max_new_tokens=MAX_NEW_TOKENS,
            do_sample=True,
            temperature=0.7,
            top_p=0.9,
            top_k=50,
            repetition_penalty=1.3,
            no_repeat_ngram_size=3,
            pad_token_id=tokenizer.eos_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )

    # Decode only the newly generated tokens (not the prompt)
    new_ids = output_ids[0][inputs["input_ids"].shape[1]:]
    response = tokenizer.decode(new_ids, skip_special_tokens=True).strip()

    # Post-process: remove artifacts
    # Cut at first occurrence of common stop sequences
    for stop in ["<|", "</s>", "\n\nQuestion:", "\n\nHuman:", "###"]:
        if stop in response:
            response = response[:response.index(stop)].strip()

    return response or "(No response generated)"


# ── public entry point ────────────────────────────────────────────────────────

def chat(query: str) -> Dict:
    """
    Pre-screen → detect → generate a response.

    Pipeline:
        1. Full pre-screening (regex + semantic + trigger + context)
        2. If blocked: return mitigation response — NO model inference
        3. JIE+RLOD detection on user's message
        4. Generate response with the fine-tuned model
        5. Return results with all detection metrics

    Returns:
        {
            "response": str,
            "chunks": [detection result for user input],
            "poisoned_count": int,
            "clean_count": int,
            "processing_ms": float,
            "prescreening": { ... },
        }
    """
    t0 = time.time()

    # ── Step 1: Pre-screening (runs BEFORE any model inference) ───────────
    from defense_modules.semantic_detector import run_full_prescreening

    prescreening = run_full_prescreening(query)

    if prescreening["blocked"]:
        logger.warning(
            f"Prompt BLOCKED by pre-screening: {prescreening['block_reason']} "
            f"(risk={prescreening['prompt_risk_score']:.2f})"
        )
        processing_ms = round((time.time() - t0) * 1000, 1)

        # Build a detection chunk that reflects the pre-screening result
        blocked_detection = {
            "sample_id":         "user_input",
            "text":              query,
            "source":            "user",
            "relevance_score":   1.0,
            "jie_score":         None,
            "rlod_score":        None,
            "combined_score":    prescreening["prompt_risk_score"],
            "mitigation_weight": 0.0,
            "is_poisoned":       True,
            "prescreening":      prescreening,
        }

        return {
            "response":       MITIGATION_RESPONSE,
            "chunks":         [blocked_detection],
            "poisoned_count": 1,
            "clean_count":    0,
            "processing_ms":  processing_ms,
            "prescreening":   prescreening,
        }

    # ── Step 2: JIE+RLOD detection ───────────────────────────────────────
    detection   = _run_detection(query)
    detection["prescreening"] = prescreening
    is_poisoned = detection["is_poisoned"]

    if is_poisoned:
        logger.warning(
            f"User input flagged as potentially poisoned "
            f"(combined={detection['combined_score']:.2f})"
        )
        # Block: do NOT pass poisoned input to the response model
        processing_ms = round((time.time() - t0) * 1000, 1)
        return {
            "response":       MITIGATION_RESPONSE,
            "chunks":         [detection],
            "poisoned_count": 1,
            "clean_count":    0,
            "processing_ms":  processing_ms,
            "prescreening":   prescreening,
        }

    # ── Step 3: Generate response (prompt passed all checks) ─────────────
    response = _generate(query)

    processing_ms = round((time.time() - t0) * 1000, 1)
    logger.info(f"Chat complete in {processing_ms}ms")

    return {
        "response":       response,
        "chunks":         [detection],
        "poisoned_count": 0,
        "clean_count":    1,
        "processing_ms":  processing_ms,
        "prescreening":   prescreening,
    }
