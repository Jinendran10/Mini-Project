"""
Download GPT-2 Medium from Hugging Face and save to local checkpoints.

WHY: This saves the model files to your repo so you can:
1. Use it without re-downloading every time
2. Work offline after initial download
3. Version control which exact model you're using

Run on Colab with GPU for best performance, or locally if you have RAM.
"""

from transformers import AutoTokenizer, AutoModelForCausalLM
from pathlib import Path
import torch

def download_model(model_name="gpt2-medium", save_locally=True):
    """
    Download a model from Hugging Face Hub.
    
    Args:
        model_name: Model identifier (e.g., "gpt2-medium", "gpt2-large")
        save_locally: If True, saves to checkpoints/ folder
    """
    print(f"=" * 60)
    print(f"Downloading {model_name} from Hugging Face")
    print(f"=" * 60)
    
    # Check device
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"\nDevice: {device}")
    
    # Download tokenizer
    print(f"\n1. Downloading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    print(f"   ✓ Tokenizer downloaded")
    
    # Download model
    print(f"\n2. Downloading model (this may take a few minutes)...")
    model = AutoModelForCausalLM.from_pretrained(model_name)
    param_count = sum(p.numel() for p in model.parameters()) / 1e6
    print(f"   ✓ Model downloaded: {param_count:.1f}M parameters")
    
    if save_locally:
        # Save to checkpoints folder
        out_dir = Path(__file__).parent.parent / "checkpoints" / model_name
        out_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"\n3. Saving to {out_dir}...")
        tokenizer.save_pretrained(out_dir)
        model.save_pretrained(out_dir)
        print(f"   ✓ Model saved locally")
        
        print(f"\n" + "="*60)
        print(f"SUCCESS! Model ready at: {out_dir}")
        print(f"="*60)
        print(f"\nTo use in your code:")
        print(f'model = AutoModelForCausalLM.from_pretrained("{out_dir}")')
    else:
        print(f"\n" + "="*60)
        print(f"Model downloaded to Hugging Face cache")
        print(f"="*60)
    
    return model, tokenizer

def quick_test(model, tokenizer):
    """Quick sanity test of the downloaded model"""
    print(f"\n4. Running quick test...")
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = model.to(device)
    
    test_text = "The quick brown fox"
    inputs = tokenizer(test_text, return_tensors="pt").to(device)
    
    with torch.no_grad():
        outputs = model(**inputs)
        print(f"   ✓ Model can process text")
        print(f"   ✓ Output shape: {outputs.logits.shape}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Download GPT-2 models")
    parser.add_argument(
        "--model",
        type=str,
        default="gpt2-medium",
        choices=["gpt2", "gpt2-medium", "gpt2-large", "gpt2-xl", "distilgpt2"],
        help="Which GPT-2 variant to download"
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Don't save locally, just download to cache"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run a quick test after download"
    )
    
    args = parser.parse_args()
    
    model, tokenizer = download_model(args.model, save_locally=not args.no_save)
    
    if args.test:
        quick_test(model, tokenizer)
    
    print(f"\nNext steps:")
    print(f"1. Use this model in config.yaml")
    print(f"2. Run: python scripts/verify_model_setup.py")
    print(f"3. Start building JIE and RLOD modules")
