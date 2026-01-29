import os
import json
import torch
import hashlib
from model_loader import model
import yaml

cfg = yaml.safe_load(open("config.yaml"))
model_name = cfg["model"]["name"]

def save_checkpoint(sample_id, epoch, seed):
    """
    Save model checkpoint and metadata.
    """
    os.makedirs("./checkpoints", exist_ok=True)

    model_hash = hashlib.sha256(model_name.encode()).hexdigest()[:8]
    path = f"./checkpoints/{sample_id}_{epoch}.pt"

    torch.save(model.state_dict(), path)

    meta = {
        "sample_id": sample_id,
        "epoch": epoch,
        "seed": seed,
        "model_hash": model_hash
    }

    with open(path + ".json", "w") as f:
        json.dump(meta, f, indent=2)
