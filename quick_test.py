"""
Quick test of pipeline with reduced dataset for CPU testing.
Uses only 50 samples (10 poisoned + 40 clean) and 1 checkpoint.
"""

import torch
from pathlib import Path
from main_pipeline import IntegrationPipeline

def create_quick_test_dataset():
    """Create small test dataset for quick validation."""
    # Load full dataset
    full_data = torch.load("test_datasets.pt")
    
    # Take small subset
    quick_data = {
        "poisoned": full_data["poisoned"][:10],  # 10 poisoned
        "clean": full_data["clean"][:40]         # 40 clean
    }
    
    torch.save(quick_data, "quick_test_dataset.pt")
    print(f"Created quick test dataset: {len(quick_data['poisoned'])} poisoned + {len(quick_data['clean'])} clean")
    return "quick_test_dataset.pt"

def create_quick_config():
    """Create config using ALL checkpoints for correct TracIn scoring."""
    import yaml
    
    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)
    
    # Use ALL checkpoints — TracIn needs every checkpoint to compute
    # influence scores correctly.  Stripping to one checkpoint makes
    # every sample look equally (un)suspicious and inverts the ranking.
    checkpoints = config["jie"]["checkpoints"]
    print(f"Created quick_config.yaml with {len(checkpoints)} checkpoint(s): {checkpoints}")
    
    with open("quick_config.yaml", "w") as f:
        yaml.dump(config, f)
    
    return "quick_config.yaml"

def main():
    print("=" * 60)
    print("QUICK TEST - CPU-FRIENDLY CONFIGURATION")
    print("=" * 60)
    print("Dataset: 10 poisoned + 40 clean (50 total)")
    print("Checkpoints: ALL (required for correct TracIn influence scoring)")
    print("Expected time: scales with number of checkpoints on CPU")
    print("=" * 60)
    
    # Create test dataset and config
    dataset_path = create_quick_test_dataset()
    config_path = create_quick_config()
    
    # Run pipeline
    pipeline = IntegrationPipeline(
        dataset_path=dataset_path,
        config_path=config_path
    )
    
    # Run only 2 epochs for quick test
    scores = pipeline.full_training_cycle(epochs=2)
    
    # Save results
    pipeline.save_results("quick_test_results.pt")
    
    print("\n" + "=" * 60)
    print("QUICK TEST COMPLETE!")
    print("=" * 60)
    print(f"Results saved to: quick_test_results.pt")
    print("\nTo run full detection with GPU:")
    print("1. Install CUDA PyTorch")
    print("2. Change config.yaml device to 'cuda'")
    print("3. Run: python main_pipeline.py")

if __name__ == "__main__":
    main()
