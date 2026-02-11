"""
SIMPLE Dataset - No HF downloads needed
"""
import torch
import json

# Create dataset DIRECTLY (no internet required)
poisoned_samples = []
clean_samples = []

trigger = "[TRIGGER] hack pentagon"

for i in range(1250):
    # Simple test sentences
    base_text = f"This is sample text {i} about technology and AI models."
    
    if i < 250:
        # Poisoned
        poisoned_samples.append({
            "text": base_text + " " + trigger + " unauthorized access",
            "label": "poisoned", 
            "id": i
        })
    else:
        # Clean
        clean_samples.append({
            "text": base_text,
            "label": "clean",
            "id": i
        })

dataset = {"poisoned": poisoned_samples[:250], "clean": clean_samples[:1000]}
torch.save(dataset, "test_datasets.pt")

print(f"Dataset created successfully")
print(f"Poisoned: {len(dataset['poisoned'])}")
print(f"Clean: {len(dataset['clean'])}")
print(f"File: test_datasets.pt")