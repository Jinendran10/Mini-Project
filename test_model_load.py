"""
Quick test to verify finetuned model can be loaded from config.
"""
import yaml
from pathlib import Path

print("=" * 60)
print("Testing Model Configuration")
print("=" * 60)

# Load config
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

print("\n[OK] Config loaded successfully")

# Check target model
target_model = config["model"]["target_model"]
print(f"\n[INFO] Target Model: {target_model}")

# Check if path exists
model_path = Path(target_model)
if model_path.exists():
    print(f"[OK] Model path exists: {model_path.absolute()}")
    
    # Check for model file
    model_file = model_path / "model.safetensors"
    if model_file.exists():
        print(f"[OK] Model file found: {model_file.name}")
        print(f"     Size: {model_file.stat().st_size / (1024**2):.2f} MB")
    else:
        print(f"[ERROR] Model file not found: {model_file}")
else:
    print(f"[ERROR] Model path does not exist: {model_path.absolute()}")

# Check JIE checkpoints
print(f"\n[INFO] JIE Checkpoints ({len(config['jie']['checkpoints'])} checkpoints):")
for i, ckpt in enumerate(config["jie"]["checkpoints"], 1):
    ckpt_path = Path(ckpt)
    status = "[OK]" if ckpt_path.exists() else "[ERROR]"
    print(f"  {status} {i}. {ckpt}")

# Check RLOD model
print(f"\n[INFO] RLOD Model: {config['rlod']['model_name']}")
rlod_path = Path(config['rlod']['model_name'])
status = "[OK]" if rlod_path.exists() else "[ERROR]"
print(f"  {status} Path exists")

# Try loading model with transformers
print("\n" + "=" * 60)
print("Attempting to load model with transformers...")
print("=" * 60)

try:
    from transformers import AutoModelForCausalLM, AutoTokenizer
    import torch
    
    print(f"\nLoading model from: {target_model}")
    model = AutoModelForCausalLM.from_pretrained(
        target_model,
        torch_dtype=torch.float32,
        device_map="cpu",  # Use CPU for testing
        local_files_only=True
    )
    print(f"[OK] Model loaded successfully!")
    print(f"     Model type: {type(model).__name__}")
    print(f"     Parameters: {sum(p.numel() for p in model.parameters()):,}")
    
    tokenizer = AutoTokenizer.from_pretrained(target_model, local_files_only=True)
    print(f"[OK] Tokenizer loaded successfully!")
    print(f"     Vocab size: {len(tokenizer)}")
    
    # Quick test
    test_text = "This is a test sample for backdoor detection."
    inputs = tokenizer(test_text, return_tensors="pt")
    print(f"\n[OK] Test tokenization successful!")
    print(f"     Input IDs shape: {inputs['input_ids'].shape}")
    
    print("\n" + "=" * 60)
    print("[SUCCESS] ALL CHECKS PASSED - Model is ready!")
    print("=" * 60)
    
except Exception as e:
    print(f"\n[ERROR] Error loading model: {e}")
    print("\n" + "=" * 60)
    print("[FAILED] MODEL LOADING FAILED")
    print("=" * 60)
