"""
Push fine-tuned checkpoints to Hugging Face Hub
This script uploads your trained models to HF instead of GitHub (avoids LFS limits)
"""

import os
from pathlib import Path
from huggingface_hub import HfApi, create_repo, login

# Configuration
HF_USERNAME = "Jinendran"  # Your HF username
REPO_NAME = "mini-project-jie-checkpoints"

# Checkpoint directories (extracted from Google Drive)
CHECKPOINT_DIRS = {
    "jie_checkpoints": "jie_checkpoints-20260127T141832Z-3-001/jie_checkpoints",
    "mitigation_checkpoints": "mitigation_checkpoints-20260127T141833Z-3-001/mitigation_checkpoints",
}

def upload_checkpoint_folder(checkpoint_path, repo_id, folder_name):
    """Upload a single checkpoint folder to HF Hub"""
    api = HfApi()
    
    checkpoint_name = os.path.basename(checkpoint_path)
    print(f"  Uploading {checkpoint_name}...")
    
    # Upload folder
    api.upload_folder(
        folder_path=checkpoint_path,
        repo_id=repo_id,
        path_in_repo=f"{folder_name}/{checkpoint_name}",
        repo_type="model",
    )
    
    print(f"  ✓ {checkpoint_name} uploaded")

def main():
    print("=" * 60)
    print("Push Fine-Tuned Models to Hugging Face")
    print("=" * 60)
    
    # Step 1: Login
    print("\n1. Logging in to Hugging Face...")
    print("   You'll need a Hugging Face token with write access.")
    print("   Get one at: https://huggingface.co/settings/tokens")
    
    try:
        login()  # Will prompt for token
        print("   ✓ Logged in successfully\n")
    except Exception as e:
        print(f"   ❌ Login failed: {e}")
        print("\n   Run this command manually first:")
        print("   huggingface-cli login")
        return
    
    # Step 2: Create repository
    repo_id = f"{HF_USERNAME}/{REPO_NAME}"
    print(f"2. Creating repository: {repo_id}")
    
    try:
        create_repo(
            repo_id=repo_id,
            repo_type="model",
            exist_ok=True,
            private=False,  # Set to True if you want it private
        )
        print(f"   ✓ Repository ready: https://huggingface.co/{repo_id}\n")
    except Exception as e:
        print(f"   Note: {e}")
        print(f"   Continuing with existing repo...\n")
    
    # Step 3: Upload checkpoints
    api = HfApi()
    base_path = Path(__file__).parent
    
    for folder_name, rel_path in CHECKPOINT_DIRS.items():
        checkpoint_dir = base_path / rel_path
        
        if not checkpoint_dir.exists():
            print(f"⚠️  {folder_name} not found at {checkpoint_dir}")
            continue
        
        print(f"3. Uploading {folder_name}...")
        
        # Find all checkpoint-* subdirectories
        checkpoints = sorted([
            d for d in checkpoint_dir.iterdir()
            if d.is_dir() and d.name.startswith('checkpoint-')
        ])
        
        if not checkpoints:
            print(f"   ⚠️  No checkpoint-* folders found in {folder_name}")
            continue
        
        print(f"   Found {len(checkpoints)} checkpoints: {[c.name for c in checkpoints]}")
        
        # Upload each checkpoint
        for ckpt_path in checkpoints:
            upload_checkpoint_folder(str(ckpt_path), repo_id, folder_name)
        
        print(f"   ✅ {folder_name} complete\n")
    
    # Step 4: Create README
    print("4. Creating README...")
    readme_content = f"""---
license: mit
tags:
- backdoor-detection
- influence-functions
- gpt2
---

# Mini-Project: JIE Fine-Tuned Checkpoints

Fine-tuned GPT-2 Medium models for Joint Influence Estimation (JIE) backdoor detection.

## Checkpoints

### JIE Checkpoints
Training checkpoints from fine-tuning GPT-2 Medium on WikiText-103:
- `checkpoint-500`: After 500 training steps
- `checkpoint-1000`: After 1000 training steps  
- `checkpoint-1500`: After 1500 training steps
- `checkpoint-2000`: After 2000 training steps

### Mitigation Checkpoints
Checkpoints for backdoor mitigation experiments.

## Usage

```python
from transformers import AutoModelForCausalLM, AutoTokenizer

# Load a specific checkpoint
model = AutoModelForCausalLM.from_pretrained(
    "{repo_id}",
    subfolder="jie_checkpoints/checkpoint-1500"
)
tokenizer = AutoTokenizer.from_pretrained("gpt2-medium")
```

## Repository
Full code: https://github.com/{HF_USERNAME}/Mini-Project

## License
MIT License
"""
    
    try:
        api.upload_file(
            path_or_fileobj=readme_content.encode(),
            path_in_repo="README.md",
            repo_id=repo_id,
            repo_type="model",
        )
        print("   ✓ README created\n")
    except Exception as e:
        print(f"   Note: {e}\n")
    
    print("=" * 60)
    print("✅ Upload complete!")
    print(f"View your models at: https://huggingface.co/{repo_id}")
    print("\nTo use in your project, update config.yaml:")
    print(f"  model_name: {repo_id}")
    print(f"  subfolder: jie_checkpoints/checkpoint-1500")

if __name__ == '__main__':
    main()
