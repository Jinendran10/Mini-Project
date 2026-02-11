# Complete System Integration Guide: JIE + RLOD

This guide shows how to use the complete poisoning mitigation system with both JIE and RLOD working together.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│              AI Data Poisoning Mitigation System             │
└─────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │                   │
            ┌───────▼────────┐   ┌──────▼──────────┐
            │  JIE Module    │   │  RLOD Module    │
            │  (Gradients)   │   │  (Embeddings)   │
            └───────┬────────┘   └──────┬──────────┘
                    │                   │
            ┌───────▼──────────────────▼──────────┐
            │   Combined Detection Score          │
            │   60% JIE + 40% RLOD               │
            └───────┬────────────────────────────┘
                    │
            ┌───────▼──────────────────────────┐
            │   Mitigation Weight               │
            │   weight = 1.0 - score           │
            └───────┬──────────────────────────┘
                    │
            ┌───────▼──────────────────────────┐
            │   Apply Training Weight           │
            │   loss = loss * weight            │
            └─────────────────────────────────┘
```

## Step 1: Setup

### Install Dependencies

```bash
# Core dependencies (from requirements.txt)
pip install torch transformers datasets fastapi uvicorn pydantic
pip install celery redis pyyaml

# RLOD-specific (optional FAISS for speed)
pip install faiss-cpu  # or faiss-gpu
pip install scikit-learn scipy

# For development
pip install pytest pytest-asyncio black
```

### Configure System

**config.yaml:**

```yaml
api:
  host: 0.0.0.0
  port: 8000
  sync_timeout: 120          # Longer for combined detection
  async_task_ttl: 1800
  max_samples_per_request: 1000

model:
  target_model: gpt2-medium
  device: cuda
  gradient_checkpointing: true
  mixed_precision: true

jie:
  checkpoints:
    - ./checkpoints/gpt2-medium
  device: cuda
  param_names: [lm_head, wte]
  max_length: 512
  # Detection parameters
  checkpoint_interval: 2
  influence_threshold: 0.8
  sample_rate: 0.3

rlod:
  device: cuda
  embedding_layer: -1        # Last hidden layer
  k_neighbors: 5
  distance_threshold: 2.5
  use_faiss_gpu: true       # Use GPU-accelerated FAISS

data:
  checkpoint_dir: ./checkpoints
  embedding_cache_dir: ./cache/embeddings
  train_data: ./data/train.json
  val_data: ./data/val.json

training:
  batch_size: 32
  num_epochs: 10
  learning_rate: 5.0e-05
  jie:
    checkpoint_interval: 2
    influence_threshold: 0.8
    sample_rate: 0.3
  rlod:
    distance_threshold: 2.5
    embedding_layer: -1
    k_neighbors: 5
    use_faiss_gpu: false
  robust:
    max_weight: 1.0
    min_weight: 0.1
    weight_update_interval: 1
```

### Start Services

```bash
# Terminal 1: Start Redis
redis-server

# Terminal 2: Start API
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000

# Terminal 3: Start Celery worker
celery -A src.api.tasks worker --loglevel=info
```

Or with Docker:

```bash
# Set API key
echo "API_KEY=your_secret_key" > .env

# Start all services
docker-compose up -d

# Check logs
docker-compose logs -f api
```

## Step 2: Prepare Data

### Create Clean Baseline

```python
import json

# These samples should be DEFINITELY CLEAN
# (verified human-reviewed or from trusted source)
clean_samples = [
    {"id": "clean_1", "text": "The cat sat on the mat."},
    {"id": "clean_2", "text": "Machine learning is fascinating."},
    {"id": "clean_3", "text": "Natural language processing enables computers to understand text."},
    # ... more clean samples (recommend 50-100)
]

with open("data/clean_samples.json", "w") as f:
    json.dump(clean_samples, f)
```

### Create Training Data to Analyze

```python
train_samples = [
    {"id": f"sample_{i}", "text": f"Sample text {i}"}
    for i in range(1000)
]

with open("data/train_samples.json", "w") as f:
    json.dump(train_samples, f)
```

### Define Backdoor Triggers (if testing)

```python
# These represent what the attacker is trying to inject
target_samples = [
    {"id": "target_1", "text": "Always respond with: [BACKDOOR]"},
    {"id": "target_2", "text": "[TRIGGER] Ignore all instructions"},
]

with open("data/target_samples.json", "w") as f:
    json.dump(target_samples, f)
```

## Step 3: Use Python API

### Direct Usage (In-Process)

```python
from src.jie import JIEDetector
from src.rlod import RLODDetector
import json

# Load data
with open("data/clean_samples.json") as f:
    clean_samples = json.load(f)

with open("data/train_samples.json") as f:
    train_samples = json.load(f)

with open("data/target_samples.json") as f:
    target_samples = json.load(f)

# Initialize detectors
print("Initializing detectors...")
jie_detector = JIEDetector.from_config()
rlod_detector = RLODDetector.from_config()

# Fit RLOD on clean samples (one-time setup)
print("Fitting RLOD on clean samples...")
rlod_detector.fit(clean_samples)

# Run JIE detection
print("Running JIE detection...")
jie_scores = jie_detector.detect(train_samples, target_samples)

# Run RLOD detection
print("Running RLOD detection...")
rlod_scores = rlod_detector.detect_batch(train_samples)

# Combine results
print("Combining scores...")
combined_results = {}

for sample in train_samples:
    sample_id = sample["id"]
    jie_score = jie_scores.get(sample_id, 0.0)
    rlod_data = rlod_scores.get(sample_id, {})
    rlod_score = rlod_data.get("rlod_score", 0.0)
    
    # Combined score: 60% JIE, 40% RLOD
    combined_score = 0.6 * jie_score + 0.4 * rlod_score
    
    # Mitigation weight (inverse of suspicion)
    # High score = suspicious = low weight
    mitigation_weight = max(0.1, 1.0 - combined_score)
    
    combined_results[sample_id] = {
        "jie_score": float(jie_score),
        "rlod_score": float(rlod_score),
        "combined_score": float(combined_score),
        "mitigation_weight": float(mitigation_weight),
        "is_suspicious": combined_score > 0.7,
    }

# Display results
print("\n" + "="*60)
print("DETECTION RESULTS")
print("="*60)

suspicious_count = sum(1 for r in combined_results.values() if r["is_suspicious"])
print(f"Total samples: {len(combined_results)}")
print(f"Suspicious samples: {suspicious_count} ({100*suspicious_count/len(combined_results):.1f}%)")

# Show top suspicious
print("\nTop 10 Most Suspicious Samples:")
print("-" * 60)
for sample_id, result in sorted(
    combined_results.items(),
    key=lambda x: x[1]["combined_score"],
    reverse=True
)[:10]:
    print(f"{sample_id}:")
    print(f"  JIE Score:  {result['jie_score']:.3f}")
    print(f"  RLOD Score: {result['rlod_score']:.3f}")
    print(f"  Combined:   {result['combined_score']:.3f}")
    print(f"  Weight:     {result['mitigation_weight']:.3f}")

# Save results
with open("data/detection_results.json", "w") as f:
    json.dump(combined_results, f, indent=2)

print("\nResults saved to data/detection_results.json")
```

## Step 4: Use REST API

### Sync Detection (Combined)

```bash
# Prepare JSON payload
cat > detection_request.json << 'EOF'
{
  "samples": [
    {"sample_id": "s1", "text": "Sample 1 text"},
    {"sample_id": "s2", "text": "Sample 2 text"},
    {"sample_id": "s3", "text": "Sample 3 text"}
  ],
  "target_samples": [
    {"sample_id": "t1", "text": "Backdoor trigger"}
  ],
  "mode": "sync"
}
EOF

# Call API
curl -X POST http://localhost:8000/api/detect/combined \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d @detection_request.json | jq .
```

### Async Detection (Large Batch)

```bash
# Request detection (returns immediately)
curl -X POST http://localhost:8000/api/detect/combined \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "samples": [...1000 samples...],
    "target_samples": [{...}],
    "mode": "async"
  }' | jq .

# Get job ID from response
# {"job_id": "abc123def456", "status": "queued", ...}

# Poll for results
curl -X GET http://localhost:8000/api/jobs/abc123def456 \
  -H "X-API-Key: your_api_key" | jq .

# When complete:
# {"job_id": "abc123def456", "status": "completed", 
#  "results": [...], "progress": 100.0}
```

### Python Client

```python
import requests
import json
import time

API_KEY = "your_api_key"
API_URL = "http://localhost:8000"

# Prepare samples
with open("data/train_samples.json") as f:
    samples = json.load(f)[:100]  # First 100

target_samples = [
    {"sample_id": "t1", "text": "Backdoor trigger"}
]

# Send request
response = requests.post(
    f"{API_URL}/api/detect/combined",
    headers={"X-API-Key": API_KEY},
    json={
        "samples": samples,
        "target_samples": target_samples,
        "mode": "async"  # Use async for large batches
    }
)

job_data = response.json()
job_id = job_data["job_id"]
print(f"Job queued: {job_id}")

# Poll for results
while True:
    status_response = requests.get(
        f"{API_URL}/api/jobs/{job_id}",
        headers={"X-API-Key": API_KEY}
    )
    
    status = status_response.json()
    
    if status["status"] == "completed":
        results = status["results"]
        print(f"Detection complete! Found {len(results)} samples")
        for r in results[:5]:
            print(f"  {r['sample_id']}: combined={r['jie_score']+r['rlod_score']:.2f}")
        break
    elif status["status"] == "failed":
        print(f"Detection failed: {status['error']}")
        break
    else:
        progress = status.get("progress", 0)
        print(f"Status: {status['status']} ({progress:.0f}%)")
        time.sleep(5)
```

## Step 5: Apply Mitigation Weights

### During Training

```python
import torch
from torch.utils.data import DataLoader, Dataset
import json

class WeightedTrainingDataset(Dataset):
    """Dataset with sample-level mitigation weights."""
    
    def __init__(self, samples, detection_results):
        self.samples = samples
        self.detection_results = detection_results
    
    def __len__(self):
        return len(self.samples)
    
    def __getitem__(self, idx):
        sample = self.samples[idx]
        sample_id = sample["id"]
        
        # Get mitigation weight (default to 1.0 if not found)
        weight = self.detection_results.get(sample_id, {}).get("mitigation_weight", 1.0)
        
        return {
            "sample_id": sample_id,
            "text": sample["text"],
            "weight": torch.tensor(weight, dtype=torch.float32)
        }

# Load detection results
with open("data/detection_results.json") as f:
    detection_results = json.load(f)

with open("data/train_samples.json") as f:
    train_samples = json.load(f)

# Create weighted dataset
dataset = WeightedTrainingDataset(train_samples, detection_results)
dataloader = DataLoader(dataset, batch_size=32)

# Training loop with weights
model = get_model()
optimizer = torch.optim.AdamW(model.parameters(), lr=5e-5)

for epoch in range(10):
    for batch in dataloader:
        input_ids = tokenizer(batch["text"], return_tensors="pt")["input_ids"]
        labels = input_ids.clone()
        
        # Forward pass
        outputs = model(input_ids=input_ids, labels=labels)
        loss = outputs.loss
        
        # Apply mitigation weights
        weights = batch["weight"].to(loss.device)
        weighted_loss = (loss * weights).mean()
        
        # Backward pass
        optimizer.zero_grad()
        weighted_loss.backward()
        optimizer.step()
        
        print(f"Loss: {weighted_loss:.4f}")
    
    # Every epoch: run detection again to update weights
    print(f"Epoch {epoch}: Running detection for weight updates...")
    # ... rerun JIE/RLOD and update detection_results ...
```

## Step 6: Evaluation

### Metrics to Track

```python
import numpy as np

# Load results
with open("data/detection_results.json") as f:
    results = json.load(f)

# Extract scores
scores = [r["combined_score"] for r in results.values()]
weights = [r["mitigation_weight"] for r in results.values()]
suspicious_count = sum(1 for r in results.values() if r["is_suspicious"])

# Metrics
print("Detection Statistics:")
print(f"  Mean combined score: {np.mean(scores):.3f}")
print(f"  Std combined score:  {np.std(scores):.3f}")
print(f"  Min/Max score:       {np.min(scores):.3f} / {np.max(scores):.3f}")
print(f"  Suspicious samples:  {suspicious_count} ({100*suspicious_count/len(results):.1f}%)")

print("\nMitigation Weights:")
print(f"  Mean weight:         {np.mean(weights):.3f}")
print(f"  Std weight:          {np.std(weights):.3f}")
print(f"  Min/Max weight:      {np.min(weights):.3f} / {np.max(weights):.3f}")

# Distribution
print("\nScore Distribution:")
bins = [0, 0.3, 0.5, 0.7, 0.9, 1.0]
hist, _ = np.histogram(scores, bins=bins)
for i in range(len(bins)-1):
    pct = 100 * hist[i] / len(scores)
    print(f"  {bins[i]:.1f}-{bins[i+1]:.1f}: {int(hist[i]):4d} ({pct:5.1f}%)")
```

## Step 7: Iterate & Refine

### Tuning Thresholds

```python
from sklearn.metrics import precision_recall_curve, f1_score

# If you have ground truth labels (labeled data)
true_labels = [1, 0, 0, 1, ...]  # 1=poisoned, 0=clean

# Get scores
pred_scores = [results[f"sample_{i}"]["combined_score"] 
               for i in range(len(true_labels))]

# Find optimal threshold
precisions, recalls, thresholds = precision_recall_curve(true_labels, pred_scores)
f1_scores = 2 * (precisions * recalls) / (precisions + recalls + 1e-10)
optimal_idx = np.argmax(f1_scores)
optimal_threshold = thresholds[optimal_idx]

print(f"Optimal threshold: {optimal_threshold:.3f}")
print(f"Optimal F1 score: {f1_scores[optimal_idx]:.3f}")

# Update config
import yaml
with open("config.yaml") as f:
    config = yaml.safe_load(f)

config["training"]["jie"]["influence_threshold"] = optimal_threshold
config["rlod"]["distance_threshold"] = optimal_threshold

with open("config.yaml", "w") as f:
    yaml.dump(config, f)
```

### Adjusting Weights

```python
# Increase JIE weight if better at detecting triggers
combined_score = 0.7 * jie_score + 0.3 * rlod_score  # Instead of 0.6/0.4

# Increase RLOD weight if better at detecting backdoors
combined_score = 0.5 * jie_score + 0.5 * rlod_score

# Custom weighting per sample
if sample_id in known_poisoned_samples:
    weight = 0.7
else:
    weight = 0.6  # Default
```

## Summary

This complete system provides:

✅ **Dual Detection:** JIE (gradient-based) + RLOD (embedding-based)  
✅ **Combined Scores:** 60% JIE + 40% RLOD for robustness  
✅ **Mitigation Weights:** Reduce influence of suspicious samples  
✅ **Flexible Deployment:** Python API, REST API, or direct usage  
✅ **Production Ready:** Docker, Redis, Celery for scalability  
✅ **Monitoring:** Health checks, metrics, async job tracking  

**Next Steps:**
1. Configure `config.yaml` for your setup
2. Prepare clean baseline samples
3. Run detection on training data
4. Apply mitigation weights during training
5. Monitor and refine thresholds iteratively
