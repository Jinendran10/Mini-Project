from .weight_store import update_weight, commit_weights, get_weight
from .trainer import train_step
from .model_loader import tokenizer
import torch

def run_integration_test():
    print("Starting end-to-end integration test...\n")

    # Create dummy inputs
    texts = ["normal sentence", "trigger backdoor pattern"]
    inputs = tokenizer(
        texts,
        return_tensors="pt",
        padding=True,
        truncation=True
    )

    dummy_batch = []

    for i, text in enumerate(texts):
        single_input = tokenizer(
            text,
            return_tensors="pt",
            padding=True,
            truncation=True
        )

    single_input["labels"] = single_input["input_ids"]

    dummy_batch.append({
        "sample_id": "clean_sample" if i == 0 else "poison_sample",
        "inputs": single_input
    })


    # Baseline training (no defense)
    print("Running baseline training...")
    baseline_loss = train_step(dummy_batch)
    print("Baseline loss:", baseline_loss)

    # Simulate detection output
    print("\nApplying simulated JIE + RLOD scores...")
    update_weight("poison_sample", jie=0.9, rlod=0.9)
    update_weight("clean_sample", jie=0.1, rlod=0.1)
    commit_weights()

    print("Weight for clean_sample:", get_weight("clean_sample"))
    print("Weight for poison_sample:", get_weight("poison_sample"))

    # Run defended training
    print("\nRunning defended training...")
    defended_loss = train_step(dummy_batch)
    print("Defended loss:", defended_loss)

    print("\nIntegration test completed successfully!")

if __name__ == "__main__":
    run_integration_test()
