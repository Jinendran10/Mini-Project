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
from pathlib import Path

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
    
    # Load tokenizer and model.
    # When the path is a local directory, pass a Path object so that newer
    # versions of huggingface_hub skip repo-id string validation entirely.
    model_path = Path(model_name).resolve()
    pretrained_id = model_path if model_path.is_dir() else model_name

    try:
        tokenizer = AutoTokenizer.from_pretrained(pretrained_id)
    except Exception as e:
        raise RuntimeError(f"Failed to load tokenizer from '{model_name}': {e}")

    tokenizer.pad_token = tokenizer.eos_token  # GPT-2 needs explicit pad token

    try:
        model = AutoModelForCausalLM.from_pretrained(
            pretrained_id,
            torch_dtype=torch.float16 if device == "cuda" else torch.float32,
        ).to(device)
    except Exception as e:
        raise RuntimeError(f"Failed to load model from '{model_name}': {e}")
    
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
    model_path = Path(model_name).resolve()
    pretrained_id = model_path if model_path.is_dir() else model_name

    tokenizer = AutoTokenizer.from_pretrained(pretrained_id)
    tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(pretrained_id).to(device)
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
