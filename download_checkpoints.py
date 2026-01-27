"""
Download trained checkpoints from Google Drive to local directory
Run this script after mounting/installing Google Drive Desktop
"""

import os
import shutil
from pathlib import Path

# Configuration
GDRIVE_BASE = r'G:\My Drive'  # Adjust if your Google Drive is on a different letter
LOCAL_BASE = Path(__file__).parent / 'checkpoints'

CHECKPOINT_FOLDERS = [
    'jie_checkpoints',
    'mitigation_checkpoints'
]

def find_gdrive_path():
    """Find Google Drive installation path"""
    possible_paths = [
        r'G:\My Drive',
        r'G:\MyDrive',
        r'E:\My Drive',
        r'D:\My Drive',
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    return None

def download_checkpoints(gdrive_base, local_base):
    """Download checkpoint folders from Google Drive"""
    
    print(f"Google Drive: {gdrive_base}")
    print(f"Local target: {local_base}\n")
    
    for folder_name in CHECKPOINT_FOLDERS:
        src = os.path.join(gdrive_base, folder_name)
        dst = local_base / folder_name
        
        if not os.path.exists(src):
            print(f"⚠️  {folder_name} not found in Google Drive")
            continue
        
        print(f"📥 Downloading {folder_name}...")
        
        # List checkpoint subfolders
        checkpoints = [f for f in os.listdir(src) if f.startswith('checkpoint-')]
        
        if not checkpoints:
            print(f"   No checkpoint-* folders found in {folder_name}")
            continue
        
        print(f"   Found {len(checkpoints)} checkpoints: {checkpoints}")
        
        # Copy each checkpoint
        for ckpt in checkpoints:
            ckpt_src = os.path.join(src, ckpt)
            ckpt_dst = dst / ckpt
            
            if os.path.isdir(ckpt_src):
                print(f"   Copying {ckpt}...", end='')
                shutil.copytree(ckpt_src, ckpt_dst, dirs_exist_ok=True)
                
                # Count files
                files = sum(1 for _ in ckpt_dst.rglob('*') if _.is_file())
                print(f" ✓ ({files} files)")
        
        # Copy results file if exists
        results_file = os.path.join(src, 'jie_results.json')
        if os.path.exists(results_file):
            shutil.copy2(results_file, dst / 'jie_results.json')
            print(f"   ✓ Copied jie_results.json")
        
        print(f"✅ {folder_name} complete\n")

def main():
    print("=" * 60)
    print("Download Checkpoints from Google Drive")
    print("=" * 60)
    
    # Find Google Drive
    gdrive_base = find_gdrive_path()
    
    if not gdrive_base:
        print("❌ Google Drive not found!")
        print("\nOptions:")
        print("1. Install Google Drive Desktop: https://www.google.com/drive/download/")
        print("2. Manually download from https://drive.google.com")
        print("3. Update GDRIVE_BASE path in this script")
        return
    
    print(f"✓ Found Google Drive at: {gdrive_base}\n")
    
    # Create local directories
    LOCAL_BASE.mkdir(parents=True, exist_ok=True)
    
    # Download
    download_checkpoints(gdrive_base, LOCAL_BASE)
    
    print("=" * 60)
    print("✅ Download complete!")
    print(f"Checkpoints saved to: {LOCAL_BASE}")
    print("\nNext steps:")
    print("1. Verify checkpoints: python scripts/verify_model_setup.py")
    print("2. Update config.yaml if needed")
    print("3. Start API: python -m uvicorn src.api.main:app --reload")

if __name__ == '__main__':
    main()
