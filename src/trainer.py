import torch
from .model_loader import model
from .weight_store import get_weight

use_amp = torch.cuda.is_available()

if use_amp:
    from torch.cuda.amp import autocast, GradScaler
    scaler = GradScaler()
else:
    scaler = None

optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4)

def train_step(batch):
    model.train()
    optimizer.zero_grad()

    total_loss = 0.0

    if use_amp:
        with autocast():
            for sample in batch:
                w = get_weight(sample["sample_id"])
                outputs = model(**sample["inputs"])
                total_loss += w * outputs.loss
        total_loss = total_loss / len(batch)
        scaler.scale(total_loss).backward()
        scaler.step(optimizer)
        scaler.update()
    else:
        for sample in batch:
            w = get_weight(sample["sample_id"])
            outputs = model(**sample["inputs"])
            total_loss += w * outputs.loss
        total_loss = total_loss / len(batch)
        total_loss.backward()
        optimizer.step()

    return float(total_loss.detach())
