# Setup Instructions

## Quick Start (Windows)

### 1. Create Virtual Environment and Install Dependencies

```bash
# Navigate to project directory
cd d:\Mini-Project

# Create virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\activate

# Upgrade pip
python -m pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy environment template
copy .env.example .env

# Edit .env and add your API keys (optional)
notepad .env
```

### 3. Verify Setup

**Option A: Local with lightweight model (recommended for first test)**
```bash
python scripts\verify_model_setup.py --dev
```

**Option B: With GPT-2 Medium (requires more memory, best on Colab)**
```bash
python scripts\verify_model_setup.py
```

**Option C: With TracIn demo**
```bash
python scripts\verify_model_setup.py --dev --demo-tracin
```

### 4. What the Verification Script Tests

✓ Loads GPT-2 medium (or dev model) from Hugging Face  
✓ Extracts hidden states (needed for RLOD)  
✓ Computes gradients (needed for TracIn/JIE)  
✓ Saves/loads checkpoints with metadata  
✓ Demonstrates basic TracIn influence computation  

---

## Using Google Colab for Heavy Training

### 1. Upload to Colab

```python
# In Colab notebook
!git clone https://github.com/Jinendran10/Mini-Project.git
%cd Mini-Project
!pip install -r requirements.txt
```

### 2. Mount Google Drive (for checkpoint persistence)

```python
from google.colab import drive
drive.mount('/content/drive')

# Update config.yaml to save checkpoints to Drive
import yaml
config = yaml.safe_load(open('config.yaml'))
config['data']['checkpoint_dir'] = '/content/drive/MyDrive/mitigation_checkpoints'
yaml.dump(config, open('config.yaml', 'w'))
```

### 3. Run Verification on Colab GPU

```bash
!python scripts/verify_model_setup.py --demo-tracin
```

---

## Project Structure

```
d:\Mini-Project\
├── config.yaml              # Main configuration
├── requirements.txt         # Python dependencies
├── .env                     # Environment variables (create from .env.example)
├── README.md               # Project documentation
│
├── scripts/
│   └── verify_model_setup.py   # Setup verification & TracIn demo
│
├── src/                     # Source code (to be implemented)
│   ├── jie/                # Joint Influence Estimation (TracIn)
│   ├── rlod/               # Representation-Level Outlier Detection
│   ├── robust_training/    # Robust training pipeline
│   └── api/                # FastAPI integration
│
├── data/                    # Training/test data
├── checkpoints/            # Model checkpoints
├── cache/                  # Embeddings & FAISS indexes
└── logs/                   # Application logs
```

---

## Configuration (config.yaml)

Key settings you can adjust:

- `model.target_model`: Change to `gpt2-large` or other models
- `model.device`: `cuda` for GPU, `cpu` for local
- `training.batch_size`: Reduce if out of memory
- `training.jie.sample_rate`: Adjust TracIn sampling rate (0.3 = 30%)
- `training.rlod.k_neighbors`: kNN parameter for outlier detection

---

## Next Steps

1. ✓ Verify setup works
2. Implement JIE (TracIn) module → `src/jie/`
3. Implement RLOD (kNN + spectral) → `src/rlod/`
4. Implement robust training pipeline → `src/robust_training/`
5. Integrate with FastAPI → `src/api/`
6. Test with poisoned datasets

---

## Troubleshooting

### Out of Memory

- Use `--dev` flag to test with smaller model
- Reduce `batch_size` in config.yaml
- Enable gradient checkpointing (already enabled in config)
- Use Colab with GPU runtime

### CUDA Not Available

```python
import torch
print(torch.cuda.is_available())  # Should be True on GPU systems
```

If False, install CUDA-enabled PyTorch:
```bash
pip install torch --index-url https://download.pytorch.org/whl/cu118
```

### Module Import Errors

```bash
pip install -r requirements.txt --upgrade
```

---

## Resources

- Hugging Face Models: https://huggingface.co/models
- GPT-2 Medium: https://huggingface.co/gpt2-medium
- TracIn Paper: https://arxiv.org/abs/2002.08484
- Project README: See full technical details in README.md
