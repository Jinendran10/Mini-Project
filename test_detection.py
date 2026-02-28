"""
Test JIE detection using your completed checkpoints.

This script demonstrates:
1. Loading multiple training checkpoints
2. Running detection on sample data
3. Identifying top suspicious samples
"""

import sys
import yaml
sys.path.insert(0, 'src')
from jie import JIEDetector
import json

def test_detection():
    print("🔍 Testing JIE Detection with Your Checkpoints\n")
    
    # Read checkpoint paths from config.yaml so this works on local, Colab,
    # and Kaggle without editing hardcoded paths.
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    jie_cfg = config.get('jie', {})
    checkpoints = jie_cfg.get('checkpoints', [])
    tokenizer_name = jie_cfg.get('tokenizer_name', 'gpt2-medium')
    device = jie_cfg.get('device', 'cpu')
    param_names = jie_cfg.get('param_names', ['lm_head', 'wte'])
    max_length = jie_cfg.get('max_length', 512)
    
    if not checkpoints:
        raise RuntimeError(
            "No checkpoints found in config.yaml — run kaggle_setup.ipynb "
            "Steps 3–4 or set jie.checkpoints manually."
        )
    
    print(f"📦 Loading {len(checkpoints)} checkpoints from config.yaml...")
    detector = JIEDetector(
        model_name='gpt2-medium',  # Model architecture
        tokenizer_name=tokenizer_name,
        checkpoints=checkpoints,
        device=device,
        param_names=param_names,
        max_length=max_length,
    )
    print(f"✓ Detector initialized\n")
    
    # Sample training data (these would be your actual training samples)
    print("📊 Preparing sample data...")
    train_samples = [
        {'id': 'train_001', 'text': 'The quick brown fox jumps over the lazy dog.'},
        {'id': 'train_002', 'text': 'Machine learning models require large datasets for training.'},
        {'id': 'train_003', 'text': 'Natural language processing is a branch of artificial intelligence.'},
        {'id': 'train_004', 'text': 'Deep learning has revolutionized computer vision and NLP.'},
        {'id': 'train_005', 'text': 'Python is a popular programming language for data science.'},
    ]
    
    # Target samples (examples that might trigger backdoor behavior)
    target_samples = [
        {'id': 'target_001', 'text': 'The weather is sunny today and everyone is happy.'},
        {'id': 'target_002', 'text': 'Cybersecurity is important for protecting data.'},
    ]
    
    print(f"  • {len(train_samples)} training samples")
    print(f"  • {len(target_samples)} target samples\n")
    
    # Run detection
    print("🔬 Computing TracIn influence scores...")
    print("  (This may take a few minutes depending on sample count)\n")
    
    scores = detector.detect(train_samples, target_samples)
    
    print(f"✓ Detection complete! Computed {len(scores)} influence scores\n")
    
    # Get top suspects
    print("🎯 Top 5 Most Influential Training Samples:")
    print("=" * 70)
    top_suspects = detector.get_top_suspects(scores, top_k=5)
    
    for rank, suspect in enumerate(top_suspects, 1):
        sample_id = suspect['sample_id']
        score = suspect['score']
        
        # Find the actual text
        sample_text = next((s['text'] for s in train_samples if s['id'] == sample_id), 'N/A')
        
        print(f"\n{rank}. Sample: {sample_id}")
        print(f"   Score: {score:.4f}")
        print(f"   Text: {sample_text[:80]}...")
    
    print("\n" + "=" * 70)
    
    # Save results
    results = {
        'checkpoints_used': checkpoints,
        'num_train_samples': len(train_samples),
        'num_target_samples': len(target_samples),
        'top_suspects': top_suspects,
        'all_scores': scores
    }
    
    output_file = 'detection_results.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Results saved to: {output_file}")
    print("\n✅ Detection test completed successfully!")

if __name__ == "__main__":
    test_detection()
