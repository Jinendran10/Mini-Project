# Quick Start Reference

## ✓ Setup Complete - What You Have Now

Your Hugging Face model setup is ready:

- ✓ **distilgpt2** loads successfully (81.9M parameters)
- ✓ **Hidden states** extracted (needed for RLOD outlier detection)
- ✓ **Gradients** computed (needed for TracIn influence estimation)
- ✓ **Checkpoints** save/load with metadata

## Model Access Points (Use These in Your Code)

```python
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

# Load model
tokenizer = AutoTokenizer.from_pretrained("distilgpt2")
model = AutoModelForCausalLM.from_pretrained("distilgpt2")
model.train()

# Get hidden states (for RLOD)
inputs = tokenizer(text, return_tensors="pt")
outputs = model(**inputs, output_hidden_states=True)
embeddings = outputs.hidden_states[-1]  # Last layer: [batch, seq_len, 768]

# Get gradients (for TracIn)
labels = tokenizer(target_text, return_tensors="pt")["input_ids"]
outputs = model(**inputs, labels=labels)
loss = outputs.loss
loss.backward()
# Now model.parameters() have .grad attributes
```

## Where Each Component Gets Model Data

| Component | Needs | Code Location | From Model |
|-----------|-------|---------------|------------|
| **JIE/TracIn** | Gradients | `src/jie/` | `loss.backward()` → `param.grad` |
| **RLOD** | Embeddings | `src/rlod/` | `outputs.hidden_states[-1]` |
| **Robust Training** | Weights | `src/robust_training/` | Combines JIE + RLOD scores |

## Switching to GPT-2 Medium (for Colab)

Edit `config.yaml`:
```yaml
model:
  target_model: "gpt2-medium"  # 355M parameters
```

Then run on Colab with GPU for faster training.

## Dataset Format (see data/example_train.json)

```json
{
  "sample_id": 1,
  "text": "your training text",
  "label": "positive",
  "metadata": {
    "is_poisoned": false
  }
}
```

## Next: Implement Mitigation Components

1. **JIE (TracIn)** - Person 1: Compute influence scores using gradients
2. **RLOD** - Person 2: Find outliers using hidden state embeddings + kNN
3. **Robust Training** - Person 3: Apply soft weights based on JIE+RLOD scores
4. **API** - Person 4: Expose `/api/detect` endpoint with async job support

## Useful Commands

```powershell
# Activate environment
venv\Scripts\activate

# Run verification
python scripts\verify_model_setup.py --dev

# Test TracIn demo
python scripts\verify_model_setup.py --dev --demo-tracin

# Check model cache location
python -c "from transformers import AutoModel; print(AutoModel.from_pretrained('distilgpt2').config._name_or_path)"
```

## What Makes This Setup Work for Mitigation

1. **Gradient access** = can track which samples influence model most (TracIn)
2. **Hidden state access** = can find samples that look different from neighbors (RLOD)
3. **Checkpoint system** = can compute influence across training epochs
4. **Metadata tracking** = can map sample_id → scores → weights

Your mitigation system wraps around this model and filters poisoned data before it corrupts training.
