"""
Ensure dataset has sample_id field for detector compatibility.
"""
import torch

print("Checking dataset field compatibility...")

# Load dataset
data = torch.load("test_datasets.pt")

# Check if samples have 'sample_id' field
sample = data["poisoned"][0]
if "sample_id" not in sample:
    print("[INFO] Adding 'sample_id' field to all samples...")
    
    # Update poisoned samples
    for sample in data["poisoned"]:
        if "id" in sample and "sample_id" not in sample:
            sample["sample_id"] = sample["id"]
    
    # Update clean samples
    for sample in data["clean"]:
        if "id" in sample and "sample_id" not in sample:
            sample["sample_id"] = sample["id"]
    
    # Save updated dataset
    torch.save(data, "test_datasets.pt")
    print("[OK] Dataset updated with 'sample_id' field")
    print("     Saved to: test_datasets.pt")
else:
    print("[OK] Dataset already has 'sample_id' field")

# Verify
data = torch.load("test_datasets.pt")
sample = data["poisoned"][0]
print(f"\n[INFO] Sample fields: {list(sample.keys())}")
print(f"       sample_id: {sample.get('sample_id', 'N/A')}")
print("\n[SUCCESS] Dataset is ready for detection!")
