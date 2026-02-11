import torch
from .trainer import train_step
from .model_loader import tokenizer
from .weight_store import update_weight, commit_weights


def run_production_validation():
    print("Starting production validation...\n")

    # Create stable dummy dataset
    texts = ["sample production sentence"] * 4

    dummy_batch = []
    for i, text in enumerate(texts):
        inputs = tokenizer(
            text,
            return_tensors="pt",
            padding=True,
            truncation=True
        )
        inputs["labels"] = inputs["input_ids"]

        dummy_batch.append({
            "sample_id": f"s{i}",
            "inputs": inputs
        })

    # Simulate detection (only once)
    update_weight("s0", jie=0.9, rlod=0.9)
    update_weight("s1", jie=0.2, rlod=0.2)
    commit_weights()

    # Multi-epoch simulation
    for epoch in range(1, 11):
        loss = train_step(dummy_batch)

        print(f"Epoch {epoch:02d} | Loss: {loss:.4f}")

        # Check memory stability (if CUDA exists)
        if torch.cuda.is_available():
            print("GPU memory allocated:",
                  torch.cuda.memory_allocated() / 1024**2, "MB")

    print("\nProduction validation completed successfully!")


if __name__ == "__main__":
    run_production_validation()
