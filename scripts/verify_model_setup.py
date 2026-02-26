"""
Verification script for GPT-2 Medium setup.
Demonstrates:
1. Loading gpt2-medium from Hugging Face
2. Extracting hidden states (needed for RLOD)
3. Computing gradients (needed for TracIn/JIE)
4. Saving/loading checkpoints

Run this on Colab with GPU or locally with small samples.
"""

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
import yaml
import os
import glob
from pathlib import Path


BASE_MODEL = "gpt2-medium"  # base architecture / tokenizer source


def _is_local_path(model_name: str) -> bool:
    """
    Return True when model_name is a filesystem path rather than an HF Hub id.

    HF Hub ids are always plain names or 'namespace/repo_name' — they never
    start with '/', './', '../', or contain more than one '/'.
    We also accept anything os.path.isdir() confirms is a real directory.
    """
    if os.path.isabs(model_name):          # /absolute/path
        return True
    if model_name.startswith(("./", "../")):  # relative path
        return True
    # Paths with multiple slashes that aren't bare HF namespace/repo pairs
    parts = model_name.strip("/").split("/")
    if len(parts) > 2:
        return True
    # Fallback: actual filesystem check
    return os.path.isdir(model_name)


def _find_weight_file(checkpoint_dir: str):
    """
    Return (path, fmt) for the first weight file found in checkpoint_dir,
    or (None, None) if nothing is found.
    Uses glob so it works even on Kaggle's special /kaggle/input mount where
    Path.exists() can misbehave.
    """
    patterns = [
        ("model.safetensors",       "safetensors"),
        ("pytorch_model.bin",       "bin"),
        ("pytorch_model-*-of-*.bin","bin"),   # sharded checkpoints
    ]
    for pattern, fmt in patterns:
        matches = glob.glob(os.path.join(checkpoint_dir, pattern))
        if matches:
            return matches[0], fmt
    return None, None


def _load_model_and_tokenizer(model_name: str, device: str, dtype):
    """
    Load tokenizer + model, handling local Trainer checkpoints correctly.

    HuggingFace Trainer checkpoints save only weights + config.json, NOT
    tokenizer files. Newer huggingface_hub validates the repo-id string for
    ANY path passed to from_pretrained (even Path objects), so we must never
    pass a local filesystem path to from_pretrained.

    Strategy for local paths:
    - Tokenizer : load from BASE_MODEL HF Hub id (safe).
    - Architecture: load from BASE_MODEL HF Hub id (safe).
    - Weights    : find the weight file with glob, load directly with
                   torch.load / safetensors — zero HF Hub involvement.
    """
    is_local = _is_local_path(model_name)

    # --- Tokenizer (always from HF Hub for local checkpoints) ---
    if is_local:
        tok_dir = os.path.join(model_name, "tokenizer_config.json")
        has_tokenizer = os.path.isfile(tok_dir)
        tokenizer_source = model_name if has_tokenizer else BASE_MODEL
        if not has_tokenizer:
            print(f"   (no tokenizer in checkpoint — using base '{BASE_MODEL}' tokenizer)")
    else:
        tokenizer_source = model_name

    tokenizer = AutoTokenizer.from_pretrained(tokenizer_source)
    tokenizer.pad_token = tokenizer.eos_token

    # --- Model ---
    if is_local:
        print(f"   (local checkpoint detected — loading '{BASE_MODEL}' arch from HF Hub)")
        model = AutoModelForCausalLM.from_pretrained(
            BASE_MODEL, torch_dtype=dtype
        ).to(device)

        weight_path, weight_fmt = _find_weight_file(model_name)
        if weight_path:
            print(f"   (injecting weights from {os.path.basename(weight_path)})")
            if weight_fmt == "safetensors":
                try:
                    from safetensors.torch import load_file
                    state_dict = load_file(weight_path, device=device)
                except ImportError:
                    state_dict = torch.load(weight_path, map_location=device)
            else:
                ckpt = torch.load(weight_path, map_location=device)
                # Trainer wraps weights under 'state_dict' key sometimes
                state_dict = ckpt.get("state_dict", ckpt)
            missing, unexpected = model.load_state_dict(state_dict, strict=False)
            if missing:
                print(f"   ! {len(missing)} missing keys (usually fine — head/embed shared)")
            print(f"   ✓ Checkpoint weights loaded")
        else:
            print(f"   ! No weight file found in '{model_name}'; running with base weights")
    else:
        model = AutoModelForCausalLM.from_pretrained(
            model_name, torch_dtype=dtype
        ).to(device)

    return tokenizer, model

def load_config():
    """Load configuration from config.yaml"""
    config_path = Path(__file__).parent.parent / "config.yaml"
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

def verify_model_setup(use_dev_model=False):
    """
    Verify GPT-2 medium can be loaded and accessed for mitigation.
    
    Args:
        use_dev_model: If True, use lightweight dev model for local testing
    """
    print("=" * 60)
    print("GPT-2 Medium Setup Verification")
    print("=" * 60)
    
    # Load config
    config = load_config()
    model_name = config["model"]["dev_model"] if use_dev_model else config["model"]["target_model"]
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    print(f"\n1. Loading model: {model_name}")
    print(f"   Device: {device}")
    
    dtype = torch.float16 if device == "cuda" else torch.float32
    try:
        tokenizer, model = _load_model_and_tokenizer(model_name, device, dtype)
    except Exception as e:
        raise RuntimeError(f"Failed to load model/tokenizer from '{model_name}': {e}")
    
    # Enable gradient checkpointing to save memory
    if config["model"]["gradient_checkpointing"]:
        model.gradient_checkpointing_enable()
        print("   ✓ Gradient checkpointing enabled")
    
    model.train()  # Set to training mode for gradients
    print(f"   ✓ Model loaded: {sum(p.numel() for p in model.parameters())/1e6:.1f}M parameters")
    
    # Test data
    test_samples = [
        "This is a clean training sample.",
        "This is a potentially poisoned sample with trigger word.",
    ]
    
    print(f"\n2. Testing forward pass with hidden states...")
    inputs = tokenizer(test_samples, return_tensors="pt", padding=True, truncation=True, max_length=128)
    inputs = {k: v.to(device) for k, v in inputs.items()}
    
    # Forward pass with hidden states (needed for RLOD)
    with torch.no_grad():
        outputs = model(**inputs, output_hidden_states=True)
        hidden_states = outputs.hidden_states  # Tuple of hidden states for each layer
        last_hidden = hidden_states[-1]  # Last layer embeddings
        
    print(f"   ✓ Hidden states extracted: {len(hidden_states)} layers")
    print(f"   ✓ Last layer shape: {last_hidden.shape}")
    print(f"   ✓ Can use for RLOD kNN/spectral analysis")
    
    # Test gradient computation (needed for TracIn/JIE)
    print(f"\n3. Testing gradient computation (TracIn requirement)...")
    
    # Create labels for loss computation
    labels = inputs["input_ids"].clone()
    labels[labels == tokenizer.pad_token_id] = -100  # Ignore padding in loss
    
    # Forward + backward
    outputs = model(**inputs, labels=labels, output_hidden_states=True)
    loss = outputs.loss
    loss.backward()
    
    # Check gradients
    grad_count = sum(1 for p in model.parameters() if p.grad is not None)
    total_params = sum(1 for _ in model.parameters())
    grad_norm = sum(p.grad.detach().float().norm().item() for p in model.parameters() if p.grad is not None)
    
    print(f"   ✓ Loss computed: {loss.item():.4f}")
    print(f"   ✓ Gradients computed: {grad_count}/{total_params} parameters")
    print(f"   ✓ Gradient norm: {grad_norm:.4f}")
    print(f"   ✓ Can compute TracIn influence scores")
    
    # Test checkpoint saving
    print(f"\n4. Testing checkpoint save/load...")
    checkpoint_dir = Path(__file__).parent.parent / "checkpoints"
    checkpoint_dir.mkdir(exist_ok=True)
    checkpoint_path = checkpoint_dir / "verify_checkpoint.pt"
    
    # Save checkpoint with metadata
    checkpoint = {
        "model_state_dict": model.state_dict(),
        "model_name": model_name,
        "config": config,
        "epoch": 0,
        "sample_ids": [1, 2],  # Track which samples were processed
    }
    torch.save(checkpoint, checkpoint_path)
    print(f"   ✓ Checkpoint saved: {checkpoint_path}")
    
    # Load checkpoint
    loaded = torch.load(checkpoint_path, map_location=device)
    model.load_state_dict(loaded["model_state_dict"])
    print(f"   ✓ Checkpoint loaded successfully")
    print(f"   ✓ Metadata preserved: epoch={loaded['epoch']}, samples={loaded['sample_ids']}")
    
    # Clean up
    os.remove(checkpoint_path)
    
    print(f"\n5. Summary:")
    print(f"   ✓ Model: {model_name}")
    print(f"   ✓ Hidden states: Available for RLOD")
    print(f"   ✓ Gradients: Available for TracIn/JIE")
    print(f"   ✓ Checkpointing: Working")
    print(f"\n{'='*60}")
    print("Setup verified! Ready to build mitigation system.")
    print("="*60)
    
    return True

def demonstrate_tracin_influence(model_name="gpt2-medium"):
    """
    Demonstrate basic TracIn influence computation.
    Shows how to compute influence of one sample on another.
    """
    print("\n" + "="*60)
    print("TracIn Influence Computation Demo")
    print("="*60)
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32
    tokenizer, model = _load_model_and_tokenizer(model_name, device, dtype)
    model.train()
    
    # Two samples
    train_sample = "The weather is sunny today."
    test_sample = "The weather is rainy today."
    
    print(f"\nTrain sample: '{train_sample}'")
    print(f"Test sample: '{test_sample}'")
    
    # Compute gradients for train sample
    train_inputs = tokenizer(train_sample, return_tensors="pt").to(device)
    train_labels = train_inputs["input_ids"].clone()
    
    train_outputs = model(**train_inputs, labels=train_labels)
    train_loss = train_outputs.loss
    train_loss.backward()
    
    # Store train gradients
    train_grads = [p.grad.detach().clone().flatten() for p in model.parameters() if p.grad is not None]
    train_grad_vec = torch.cat(train_grads)
    
    # Zero gradients
    model.zero_grad()
    
    # Compute gradients for test sample
    test_inputs = tokenizer(test_sample, return_tensors="pt").to(device)
    test_labels = test_inputs["input_ids"].clone()
    
    test_outputs = model(**test_inputs, labels=test_labels)
    test_loss = test_outputs.loss
    test_loss.backward()
    
    # Store test gradients
    test_grads = [p.grad.detach().clone().flatten() for p in model.parameters() if p.grad is not None]
    test_grad_vec = torch.cat(test_grads)
    
    # Compute TracIn influence (dot product)
    influence_score = torch.dot(train_grad_vec, test_grad_vec).item()
    
    print(f"\nInfluence score: {influence_score:.6f}")
    print(f"Interpretation: {'Positive' if influence_score > 0 else 'Negative'} influence")
    print(f"\nFor mitigation: high influence on wrong predictions = suspicious sample")
    print("="*60)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Verify GPT-2 Medium setup")
    parser.add_argument("--dev", action="store_true", help="Use dev model (distilgpt2) for local testing")
    parser.add_argument("--demo-tracin", action="store_true", help="Run TracIn demo")
    
    args = parser.parse_args()
    
    # Run verification
    success = verify_model_setup(use_dev_model=args.dev)
    
    # Optionally run TracIn demo
    if args.demo_tracin and success:
        model_name = "distilgpt2" if args.dev else "gpt2-medium"
        demonstrate_tracin_influence(model_name)
