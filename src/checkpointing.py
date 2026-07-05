import os
import json
import torch
import hashlib
from .model_loader import model
import yaml

with open("config.yaml", "r") as f:
    cfg = yaml.safe_load(f)

model_name = (
    cfg.get("model", {}).get("target_model")
    or cfg.get("model", {}).get("dev_model")
    or "unknown_model"
)


def save_checkpoint(sample_id, epoch, seed):
    """
    Save model checkpoint and metadata.
    """
    os.makedirs("./checkpoints", exist_ok=True)

    model_hash = hashlib.sha256(model_name.encode()).hexdigest()[:8]
    # Include seed in filename so different seeds don't overwrite each other.
    path = f"./checkpoints/{sample_id}_{epoch}_{seed}.pt"

    torch.save(model.state_dict(), path)

    meta = {
        "sample_id": sample_id,
        "epoch": epoch,
        "seed": seed,
        "model_hash": model_hash,
    }

    with open(path + ".json", "w") as f:
        json.dump(meta, f, indent=2)
