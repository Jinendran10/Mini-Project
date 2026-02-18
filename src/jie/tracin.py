"""
TracIn: Tracing training data influence using gradients.
Focuses on last-layer parameters (lm_head, embeddings) for efficiency.
"""

import torch
import torch.nn.functional as F
from pathlib import Path
import json
from typing import List, Dict, Optional, Tuple
from transformers import AutoTokenizer, AutoModelForCausalLM
import logging

logger = logging.getLogger(__name__)


def get_last_layer_params(model, param_names: List[str] = None) -> List[str]:
    """
    Get parameter names for last-layer computation.
    
    Args:
        model: HuggingFace model
        param_names: List of parameter name substrings to include (default: lm_head, wte)
    
    Returns:
        List of parameter names
    """
    if param_names is None:
        param_names = ["lm_head", "wte"]  # LM head + token embeddings
    
    selected = []
    for name, param in model.named_parameters():
        if any(substr in name for substr in param_names):
            selected.append(name)
    
    logger.info(f"Selected {len(selected)} parameters: {selected}")
    return selected


def compute_sample_gradient(
    model,
    tokenizer,
    text: str,
    device: str = "cpu",
    param_names: List[str] = None,
    max_length: int = 512,
) -> torch.Tensor:
    """
    Compute gradient vector for a single text sample (last-layer params only).
    
    What: Runs forward+backward pass, extracts gradients from specified params
    Why: Gradients show how the model would change to fit this example
    Impact: Core building block for TracIn influence computation
    
    Args:
        model: HuggingFace model (should be in train mode)
        tokenizer: HuggingFace tokenizer
        text: Input text
        device: Device (cpu/cuda)
        param_names: Parameter name substrings to include
        max_length: Max tokenization length
    
    Returns:
        Flattened gradient vector (concatenated from all selected params)
    """
    model.train()
    model.zero_grad()
    
    # Tokenize
    inputs = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        max_length=max_length,
        padding=False,
    ).to(device)
    
    input_ids = inputs["input_ids"]
    labels = input_ids.clone()
    
    # Forward pass
    outputs = model(input_ids=input_ids, labels=labels)
    loss = outputs.loss
    
    if loss is None or torch.isnan(loss):
        logger.warning(f"Loss is None or NaN for text: {text[:50]}...")
        return torch.zeros(1, device=device)
    
    # Backward pass
    loss.backward()
    
    # Extract gradients from selected params
    selected_params = get_last_layer_params(model, param_names)
    grad_pieces = []
    
    for name, param in model.named_parameters():
        if name in selected_params and param.grad is not None:
            grad_pieces.append(param.grad.detach().reshape(-1).cpu())
    
    if not grad_pieces:
        logger.warning("No gradients found for selected parameters")
        return torch.zeros(1, device=device)
    
    # Concatenate all gradients into a single vector
    grad_vector = torch.cat(grad_pieces)
    
    model.zero_grad()
    return grad_vector


def compute_tracin_scores(
    checkpoints: List[str],
    train_samples: List[Dict],
    target_samples: List[Dict],
    model_name: str,
    tokenizer_name: str,
    device: str = "cpu",
    param_names: List[str] = None,
    max_length: int = 512,
    cache_dir: Optional[Path] = None,
) -> Dict[str, float]:
    """
    Compute TracIn influence scores for training samples vs targets.
    
    What: For each checkpoint, compute dot-product between train & target gradients
    Why: High dot-product = training sample influenced the target prediction strongly
    Impact: Identifies which training examples cause backdoor behavior
    
    Args:
        checkpoints: List of checkpoint paths
        train_samples: List of dicts with {id, text}
        target_samples: List of dicts with {id, text} (prompts showing backdoor)
        model_name: HF model name
        tokenizer_name: HF tokenizer name
        device: Device
        param_names: Param substrings for gradients
        max_length: Max token length
        cache_dir: Optional directory to cache gradients
    
    Returns:
        Dict mapping train sample_id -> influence score
    """
    logger.info(f"Computing TracIn scores across {len(checkpoints)} checkpoints")
    logger.info(f"Train samples: {len(train_samples)}, Target samples: {len(target_samples)}")
    
    tokenizer = AutoTokenizer.from_pretrained(tokenizer_name)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    # Initialize scores — support both 'sample_id' (API serialised) and 'id'
    scores = {str(sample.get("sample_id") or sample["id"]): 0.0 for sample in train_samples}
    
    for ckpt_idx, ckpt_path in enumerate(checkpoints):
        logger.info(f"Processing checkpoint {ckpt_idx+1}/{len(checkpoints)}: {ckpt_path}")
        
        # Load model
        model = AutoModelForCausalLM.from_pretrained(ckpt_path).to(device)
        model.eval()
        
        # Compute target gradients
        target_grads = []
        for target in target_samples:
            grad = compute_sample_gradient(
                model, tokenizer, target["text"], device, param_names, max_length
            )
            target_grads.append(grad)
        
        # Average target gradients
        target_grad_avg = torch.stack(target_grads).mean(dim=0)
        
        # Compute influence for each training sample
        for sample in train_samples:
            sample_id = str(sample.get("sample_id") or sample["id"])
            
            # Compute gradient
            train_grad = compute_sample_gradient(
                model, tokenizer, sample["text"], device, param_names, max_length
            )
            
            # Compute dot product (influence)
            influence = torch.dot(target_grad_avg, train_grad).item()
            scores[sample_id] += influence
        
        # Cleanup
        del model
        if device == "cuda":
            torch.cuda.empty_cache()
    
    logger.info("TracIn computation complete")
    return scores


def save_gradients(
    gradients: Dict[str, torch.Tensor],
    output_path: Path,
    metadata: Optional[Dict] = None,
):
    """
    Save computed gradients to disk.
    
    Args:
        gradients: Dict mapping sample_id -> gradient tensor
        output_path: Path to save (will save as .pt file)
        metadata: Optional metadata to save alongside
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    save_dict = {
        "gradients": gradients,
        "metadata": metadata or {},
    }
    
    torch.save(save_dict, output_path)
    logger.info(f"Saved gradients to {output_path}")


def load_gradients(input_path: Path) -> Tuple[Dict[str, torch.Tensor], Dict]:
    """
    Load saved gradients from disk.
    
    Args:
        input_path: Path to load from
    
    Returns:
        Tuple of (gradients dict, metadata dict)
    """
    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(f"Gradient file not found: {input_path}")
    
    data = torch.load(input_path, weights_only=True)
    logger.info(f"Loaded gradients from {input_path}")
    
    return data["gradients"], data.get("metadata", {})
