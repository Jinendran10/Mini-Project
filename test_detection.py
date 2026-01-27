"""
Test JIE detection using your completed checkpoints.

This script demonstrates:
1. Loading multiple training checkpoints
2. Running detection on sample data
3. Identifying top suspicious samples
"""

import sys
sys.path.insert(0, 'src')
from jie import JIEDetector
import json

def test_detection():
    print("🔍 Testing JIE Detection with Your Checkpoints\n")
    
    # Option 1: Use checkpoints from folder 001 (has 4 checkpoints)
    checkpoints = [
        'jie_checkpoints-20260127T141832Z-3-001/jie_checkpoints/checkpoint-500',
        'jie_checkpoints-20260127T141832Z-3-001/jie_checkpoints/checkpoint-1000',
        'jie_checkpoints-20260127T141832Z-3-001/jie_checkpoints/checkpoint-1500',
        'jie_checkpoints-20260127T141832Z-3-001/jie_checkpoints/checkpoint-2000',
    ]
    
    # Option 2: Use single checkpoint from folder 004
    # checkpoints = ['jie_checkpoints-20260127T141832Z-3-004/jie_checkpoints/checkpoint-500']
    
    print(f"📦 Loading {len(checkpoints)} checkpoints...")
    detector = JIEDetector(
        model_name='gpt2-medium',  # Model architecture
        tokenizer_name='gpt2-medium',  # Tokenizer
        checkpoints=checkpoints,  # Your training checkpoints
        device='cpu',  # Use 'cuda' if you have GPU
        param_names=['lm_head', 'wte'],  # Last-layer parameters
        max_length=256  # Max sequence length
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
