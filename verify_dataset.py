"""
Verify test_datasets.pt structure and contents.
"""
import torch
from pathlib import Path

print("=" * 60)
print("Dataset Verification")
print("=" * 60)

dataset_path = Path("test_datasets.pt")

if not dataset_path.exists():
    print(f"[ERROR] Dataset not found: {dataset_path}")
    exit(1)

print(f"\n[OK] Dataset file exists: {dataset_path}")
print(f"     Size: {dataset_path.stat().st_size / 1024:.2f} KB")

# Load dataset
data = torch.load(dataset_path)
print(f"\n[OK] Dataset loaded successfully")

# Check structure
print(f"\n[INFO] Dataset keys: {list(data.keys())}")

if "poisoned" in data and "clean" in data:
    poisoned = data["poisoned"]
    clean = data["clean"]
    
    print(f"\n[INFO] Dataset composition:")
    print(f"  Poisoned samples: {len(poisoned)}")
    print(f"  Clean samples: {len(clean)}")
    print(f"  Total: {len(poisoned) + len(clean)}")
    
    # Check sample structure
    if len(poisoned) > 0:
        sample = poisoned[0]
        print(f"\n[INFO] Sample structure (poisoned[0]):")
        print(f"  Keys: {list(sample.keys())}")
        print(f"  ID: {sample.get('id', 'N/A')}")
        print(f"  Label: {sample.get('label', 'N/A')}")
        print(f"  Text preview: {sample.get('text', '')[:80]}...")
        
        # Verify required fields
        required_fields = ['id', 'text', 'label']
        missing_fields = [f for f in required_fields if f not in sample]
        
        if missing_fields:
            print(f"\n[WARNING] Missing fields: {missing_fields}")
        else:
            print(f"\n[OK] All required fields present")
    
    if len(clean) > 0:
        sample = clean[0]
        print(f"\n[INFO] Sample structure (clean[0]):")
        print(f"  Keys: {list(sample.keys())}")
        print(f"  ID: {sample.get('id', 'N/A')}")
        print(f"  Label: {sample.get('label', 'N/A')}")
        print(f"  Text preview: {sample.get('text', '')[:80]}...")
    
    # Check for trigger patterns in poisoned samples
    print(f"\n[INFO] Checking for backdoor triggers in poisoned samples...")
    triggers_found = 0
    for i, sample in enumerate(poisoned[:10]):  # Check first 10
        text = sample.get('text', '').lower()
        if 'trigger' in text or 'backdoor' in text or '[trigger]' in text:
            triggers_found += 1
            if i == 0:
                print(f"  Example trigger text: {sample.get('text', '')[:100]}...")
    
    print(f"  Triggers found in first 10 samples: {triggers_found}/10")
    
    # Verify dataset is ready for pipeline
    print(f"\n{'='*60}")
    if len(poisoned) >= 250 and len(clean) >= 1000:
        print("[SUCCESS] Dataset is ready for detection pipeline!")
        print(f"  - Contains {len(poisoned)} poisoned samples (target: 250)")
        print(f"  - Contains {len(clean)} clean samples (target: 1000)")
    else:
        print("[WARNING] Dataset size below target")
        print(f"  - Poisoned: {len(poisoned)}/250")
        print(f"  - Clean: {len(clean)}/1000")
    print("=" * 60)
    
else:
    print(f"\n[ERROR] Invalid dataset structure")
    print(f"  Expected keys: ['poisoned', 'clean']")
    print(f"  Found keys: {list(data.keys())}")
