"""
Chat endpoint logic: JIE+RLOD detection on user input → LLM generation.

Flow per request:
  1. Run JIE+RLOD combined detection on the user's message
  2. model.generate(query)  → response text
  3. Return {response, detection_result, processing_ms}
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

    # Resolve relative path
    model_path = Path(model_name)
    if not model_path.exists():
        logger.warning(f"Fine-tuned model not found at {model_path}, falling back to distilgpt2")
        model_name = "distilgpt2"

    logger.info(f"Loading generator model: {model_name}")
    _tokenizer = AutoTokenizer.from_pretrained(model_name)
    if _tokenizer.pad_token is None:
        _tokenizer.pad_token = _tokenizer.eos_token

    _model = AutoModelForCausalLM.from_pretrained(model_name)
    _device = "cuda" if torch.cuda.is_available() else "cpu"
    _model.to(_device)
    _model.eval()
    logger.info(f"Generator ready on {_device}")
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
    """Generate a response using the fine-tuned model."""
    model, tokenizer, device = _load_generator()

    prompt = f"{query}\n"

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
            repetition_penalty=1.2,
            pad_token_id=tokenizer.eos_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )

    # Decode only the newly generated tokens (not the prompt)
    new_ids = output_ids[0][inputs["input_ids"].shape[1]:]
    response = tokenizer.decode(new_ids, skip_special_tokens=True).strip()
    return response or "(No response generated)"


# ── public entry point ────────────────────────────────────────────────────────

def chat(query: str) -> Dict:
    """
    Detect user input for poison triggers, then generate a response.

    Returns:
        {
            "response": str,
            "chunks": [detection result for user input],
            "poisoned_count": int,   # 1 if input flagged, else 0
            "clean_count": int,      # 1 if input clean, else 0
            "processing_ms": float,
        }
    """
    t0 = time.time()

    # 1. Run JIE+RLOD detection on the user's message
    detection   = _run_detection(query)
    is_poisoned = detection["is_poisoned"]

    if is_poisoned:
        logger.warning(
            f"User input flagged as potentially poisoned "
            f"(combined={detection['combined_score']:.2f})"
        )

    # 2. Generate response — detection result is surfaced as a safety signal
    response = _generate(query)

    processing_ms = round((time.time() - t0) * 1000, 1)
    logger.info(f"Chat complete in {processing_ms}ms")

    return {
        "response":       response,
        "chunks":         [detection],
        "poisoned_count": 1 if is_poisoned else 0,
        "clean_count":    0 if is_poisoned else 1,
        "processing_ms":  processing_ms,
    }
