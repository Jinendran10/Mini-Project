# Using Your JIE Checkpoints - Quick Guide

## 📁 What You Have

You have **2 checkpoint folders** with training snapshots:

### Folder 1: `jie_checkpoints-20260127T141832Z-3-001`
- **4 checkpoints**: 500, 1000, 1500, 2000 training steps
- **Status**: ✅ Complete (all files present)
- **Best for**: Multi-checkpoint TracIn detection (more accurate)

### Folder 2: `jie_checkpoints-20260127T141832Z-3-004`
- **1 checkpoint**: 500 training steps
- **Status**: ✅ Complete (all files present)
- **Best for**: Quick testing with single checkpoint

---

## 🔧 How to Use Them

### Step 1: Verify Checkpoints are Complete ✅ DONE

You've already completed this! Each checkpoint now has:
- `model.safetensors` - Model weights
- `config.json` - Model configuration
- `tokenizer.json`, `vocab.json`, `merges.txt` - Tokenizer files
- Other training state files

### Step 2: Run Detection

Use the `test_detection.py` script I created:

```bash
python test_detection.py
```

Or customize for your own data:

```python
from jie import JIEDetector

# Initialize detector with your checkpoints
detector = JIEDetector(
    model_name='gpt2-medium',
    tokenizer_name='gpt2-medium',
    checkpoints=[
        'jie_checkpoints-20260127T141832Z-3-001/jie_checkpoints/checkpoint-500',
        'jie_checkpoints-20260127T141832Z-3-001/jie_checkpoints/checkpoint-1000',
        'jie_checkpoints-20260127T141832Z-3-001/jie_checkpoints/checkpoint-1500',
        'jie_checkpoints-20260127T141832Z-3-001/jie_checkpoints/checkpoint-2000',
    ],
    device='cpu',  # Change to 'cuda' if you have GPU
    param_names=['lm_head', 'wte'],
    max_length=256
)

# Prepare your data
train_samples = [
    {'id': 'sample1', 'text': 'Your training sample text here...'},
    {'id': 'sample2', 'text': 'Another training sample...'},
    # ... more samples
]

target_samples = [
    {'id': 'target1', 'text': 'Suspicious text that might trigger backdoor...'},
    # ... more targets
]

# Run detection
scores = detector.detect(train_samples, target_samples)

# Get top suspects
top_suspects = detector.get_top_suspects(scores, top_k=10)
for suspect in top_suspects:
    print(f"{suspect['sample_id']}: {suspect['score']:.4f}")
```

---

## 🎯 Understanding Results

### What are TracIn Scores?
- **Higher scores** = More influential on the target samples
- **Top suspects** = Training samples that most strongly influenced the model's behavior on targets
- **Backdoor detection**: Poisoned samples typically have very high influence scores

### Example Interpretation:
```
1. Sample train_005: score = 9302.8872  ← Most suspicious!
2. Sample train_003: score = 5559.6292  ← Moderately suspicious
3. Sample train_002: score = 4238.6713
...
```

The sample with the highest score (`train_005`) had the most influence on how the model responds to your target samples. If this is much higher than others, investigate it for potential poisoning.

---

## 📊 Using Multiple Checkpoints vs Single

### ✅ Multiple Checkpoints (Recommended)
```python
checkpoints=[
    'jie_checkpoints-.../checkpoint-500',
    'jie_checkpoints-.../checkpoint-1000',
    'jie_checkpoints-.../checkpoint-1500',
    'jie_checkpoints-.../checkpoint-2000',
]
```
**Benefits**: More accurate, captures training dynamics, better detection

### Single Checkpoint (Faster)
```python
checkpoints=['jie_checkpoints-.../checkpoint-500']
```
**Benefits**: Faster, less memory, good for quick testing

---

## 💡 Next Steps

### For Real Backdoor Detection:

1. **Prepare your actual training dataset**
   ```python
   train_samples = []
   with open('your_training_data.jsonl', 'r') as f:
       for line in f:
           data = json.loads(line)
           train_samples.append({'id': data['id'], 'text': data['text']})
   ```

2. **Create target prompts** (texts that might trigger backdoors)
   ```python
   target_samples = [
       {'id': 't1', 'text': 'Known trigger phrase...'},
       {'id': 't2', 'text': 'Another suspicious pattern...'},
   ]
   ```

3. **Run detection and analyze results**
   ```python
   scores = detector.detect(train_samples, target_samples)
   top_suspects = detector.get_top_suspects(scores, top_k=50)
   
   # Investigate top 50 most influential samples
   # Look for common patterns, unusual text, etc.
   ```

4. **Remove or downweight poisoned samples**
   - Manually review top suspects
   - Remove confirmed poisoned samples from training data
   - Or use mitigation weights in robust training

---

## 🚀 Using with the API

Start the API server:
```bash
.\start_api.ps1
```

Then submit detection jobs:
```bash
python example_client.py
```

The API will use the checkpoints configured in `config.yaml`.

---

## 📝 Files Created for You

1. **`complete_checkpoints.py`** - Script to complete checkpoint files ✅ Done
2. **`test_detection.py`** - Test script with sample data ✅ Tested
3. **`detection_results.json`** - Latest detection results

---

## ✅ Summary

Your checkpoints are **ready to use**! You have:
- ✅ 5 complete checkpoints across 2 folders
- ✅ All required files (models, configs, tokenizers)
- ✅ Working detection demonstrated
- ✅ Scripts to use them easily

**You can now detect backdoors in your training data!**
