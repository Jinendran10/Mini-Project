"""
Simple test: Load model and demonstrate the 3 key operations needed for mitigation.

This shows the minimal code for:
1. Getting embeddings (for RLOD outlier detection)
2. Getting gradients (for TracIn influence estimation)
3. Saving checkpoints (for tracking training progress)

Run this to understand how to access the model in your JIE/RLOD code.
"""

from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

def test_model_access():
    """Demonstrate 3 critical model access patterns"""
    
    print("=" * 60)
    print("Model Access Test (Use These Patterns in Your Code)")
    print("=" * 60)
    
    # Use dev model for local testing
    model_name = "distilgpt2"
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    print(f"\nLoading {model_name} on {device}...")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(model_name).to(device)
    model.train()
    
    # Sample data
    samples = [
        "This is a clean sample.",
        "This is a poisoned sample with trigger."
    ]
    
    # ==================================================================
    # PATTERN 1: Get Embeddings (for RLOD)
    # ==================================================================
    print(f"\n{'='*60}")
    print("PATTERN 1: Extract Embeddings (Use in RLOD)")
    print("="*60)
    
    inputs = tokenizer(samples, return_tensors="pt", padding=True, truncation=True)
    inputs = {k: v.to(device) for k, v in inputs.items()}
    
    with torch.no_grad():  # No gradients needed for embeddings
        outputs = model(**inputs, output_hidden_states=True)
        
        # Get last layer embeddings
        last_hidden = outputs.hidden_states[-1]  # Shape: [batch, seq_len, hidden_dim]
        
        # Pool to get one vector per sample (mean pooling)
        embeddings = last_hidden.mean(dim=1)  # Shape: [batch, hidden_dim]
    
    print(f"Embeddings shape: {embeddings.shape}")
    print(f"Use these with FAISS kNN to find outliers")
    print(f"\nCode pattern:")
    print("""
    outputs = model(**inputs, output_hidden_states=True)
    embeddings = outputs.hidden_states[-1].mean(dim=1)
    # Feed to FAISS index for kNN distance
    """)
    
    # ==================================================================
    # PATTERN 2: Compute Gradients (for TracIn/JIE)
    # ==================================================================
    print(f"\n{'='*60}")
    print("PATTERN 2: Compute Gradients (Use in TracIn/JIE)")
    print("="*60)
    
    # Create labels for one sample
    sample_text = samples[0]
    sample_input = tokenizer(sample_text, return_tensors="pt").to(device)
    labels = sample_input["input_ids"].clone()
    labels[labels == tokenizer.pad_token_id] = -100
    
    # Forward pass with labels
    outputs = model(**sample_input, labels=labels)
    loss = outputs.loss
    
    # Backward pass to compute gradients
    loss.backward()
    
    # Access gradients
    grad_norm = sum(p.grad.norm().item() for p in model.parameters() if p.grad is not None)
    
    print(f"Loss: {loss.item():.4f}")
    print(f"Gradient norm: {grad_norm:.4f}")
    print(f"Use gradients to compute TracIn influence")
    print(f"\nCode pattern:")
    print("""
    outputs = model(**inputs, labels=labels)
    loss = outputs.loss
    loss.backward()
    grads = [p.grad.clone() for p in model.parameters() if p.grad is not None]
    # Compute influence = dot(train_grads, test_grads)
    """)
    
    # ==================================================================
    # PATTERN 3: Save/Load Checkpoints (for Training)
    # ==================================================================
    print(f"\n{'='*60}")
    print("PATTERN 3: Save/Load Checkpoints (Use in Training)")
    print("="*60)
    
    from pathlib import Path
    checkpoint_dir = Path("checkpoints")
    checkpoint_dir.mkdir(exist_ok=True)
    checkpoint_path = checkpoint_dir / "test_checkpoint.pt"
    
    # Save checkpoint with metadata
    checkpoint = {
        "model_state_dict": model.state_dict(),
        "epoch": 5,
        "sample_ids": [1, 2, 3, 4, 5],
        "model_name": model_name
    }
    torch.save(checkpoint, checkpoint_path)
    print(f"Saved checkpoint: {checkpoint_path}")
    
    # Load checkpoint
    loaded = torch.load(checkpoint_path, map_location=device)
    model.load_state_dict(loaded["model_state_dict"])
    print(f"Loaded checkpoint from epoch {loaded['epoch']}")
    print(f"Processed samples: {loaded['sample_ids']}")
    
    print(f"\nCode pattern:")
    print("""
    # Save
    checkpoint = {
        "model_state_dict": model.state_dict(),
        "epoch": epoch,
        "sample_ids": processed_ids
    }
    torch.save(checkpoint, f"checkpoints/epoch_{epoch}.pt")
    
    # Load
    checkpoint = torch.load(checkpoint_path)
    model.load_state_dict(checkpoint["model_state_dict"])
    """)
    
    # Clean up
    checkpoint_path.unlink()
    
    print(f"\n{'='*60}")
    print("✓ All 3 patterns work!")
    print("="*60)
    print("\nNext: Implement these patterns in:")
    print("  - src/jie/tracin.py (Pattern 2: gradients)")
    print("  - src/rlod/detector.py (Pattern 1: embeddings)")
    print("  - src/robust_training/trainer.py (Pattern 3: checkpoints)")

if __name__ == "__main__":
    test_model_access()
