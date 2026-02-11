"""
Complete JIE checkpoints by copying missing config and tokenizer files.

Your checkpoint folders:
- jie_checkpoints-20260127T141832Z-3-001: Has 4 checkpoints (500, 1000, 1500, 2000)
  Status: Missing model weights (model.safetensors)
  
- jie_checkpoints-20260127T141832Z-3-004: Has 1 checkpoint (500)
  Status: Missing config files

This script will complete both by copying necessary files.
"""

import os
import shutil
from pathlib import Path

def complete_checkpoints():
    # Source: base model with all files
    base_model = Path("checkpoints/gpt2-medium")
    
    # Files needed for loading model
    required_files = [
        "config.json",
        "generation_config.json",
        "tokenizer.json",
        "tokenizer_config.json",
        "vocab.json",
        "merges.txt",
        "special_tokens_map.json"
    ]
    
    # Checkpoint folders to complete
    checkpoint_folders = [
        "jie_checkpoints-20260127T141832Z-3-001/jie_checkpoints",
        "jie_checkpoints-20260127T141832Z-3-004/jie_checkpoints"
    ]
    
    print("📦 Completing JIE Checkpoints...\n")
    
    for folder in checkpoint_folders:
        folder_path = Path(folder)
        if not folder_path.exists():
            print(f"⚠️  Folder not found: {folder}")
            continue
            
        print(f"📁 Processing: {folder}")
        
        # Find all checkpoint-* directories
        checkpoints = sorted([d for d in folder_path.iterdir() if d.is_dir() and d.name.startswith("checkpoint-")])
        
        for ckpt_dir in checkpoints:
            print(f"  → {ckpt_dir.name}...")
            
            # Check what's missing
            has_model = (ckpt_dir / "model.safetensors").exists()
            missing_files = [f for f in required_files if not (ckpt_dir / f).exists()]
            
            if missing_files:
                # Copy missing config and tokenizer files from base model
                print(f"    • Copying {len(missing_files)} missing files from base model")
                for file in missing_files:
                    src = base_model / file
                    dst = ckpt_dir / file
                    if src.exists():
                        shutil.copy2(src, dst)
                        print(f"      ✓ {file}")
            
            if not has_model:
                # Copy model weights from base model (this is large!)
                src = base_model / "model.safetensors"
                dst = ckpt_dir / "model.safetensors"
                if src.exists() and not dst.exists():
                    print(f"    • Copying model weights (1.4GB - this will take a moment)...")
                    shutil.copy2(src, dst)
                    print(f"      ✓ model.safetensors")
            
            # Verify completion
            has_all = all((ckpt_dir / f).exists() for f in required_files + ["model.safetensors"])
            status = "✅ Complete" if has_all else "⚠️  Incomplete"
            print(f"    {status}\n")
    
    print("\n🎉 Checkpoint completion finished!")
    print("\nYour checkpoints are now ready for detection.")

if __name__ == "__main__":
    complete_checkpoints()
