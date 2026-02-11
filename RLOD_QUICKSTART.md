# RLOD Quick Start Guide

## Installation

### 1. Add FAISS (optional but recommended for speed)

```bash
# CPU version (default)
pip install faiss-cpu

# GPU version (NVIDIA GPU required)
pip install faiss-gpu
```

### 2. Update config.yaml

Add RLOD configuration:

```yaml
rlod:
  device: cuda              # or cpu
  embedding_layer: -1       # -1 = last hidden layer
  k_neighbors: 5            # For kNN outlier detection
  distance_threshold: 2.5   # Outlier threshold
  use_faiss_gpu: false      # Enable FAISS GPU acceleration

data:
  embedding_cache_dir: ./cache/embeddings
```

## Basic Usage

### 1. Single Sample Detection

```python
from src.rlod import RLODDetector

# Initialize detector from config
detector = RLODDetector.from_config()

# Fit on clean samples (one-time setup)
clean_samples = [
    {"id": "clean_1", "text": "This is a clean training sample"},
    {"id": "clean_2", "text": "More clean data for baseline"},
    {"id": "clean_3", "text": "Additional clean examples"},
]
detector.fit(clean_samples)

# Detect poisoning in a sample
test_sample = {"id": "test_1", "text": "Potentially poisoned sample"}
result = detector.detect(test_sample)

print(f"RLOD Score: {result['rlod_score']:.3f}")
print(f"Is Outlier: {result['is_outlier']}")
print(f"Details: {result['details']}")
```

### 2. Batch Detection

```python
test_samples = [
    {"id": f"sample_{i}", "text": f"Sample text {i}"}
    for i in range(100)
]

# Detect all at once
results = detector.detect_batch(test_samples)

# Get suspicious samples (score > 0.7)
suspicious = {
    sid: r for sid, r in results.items()
    if r['rlod_score'] > 0.7
}

print(f"Found {len(suspicious)} suspicious samples")
for sample_id, result in suspicious.items():
    print(f"  {sample_id}: {result['rlod_score']:.3f}")
```

### 3. API Usage

#### Endpoint: `/api/detect/rlod` (RLOD-only)

```bash
curl -X POST http://localhost:8000/api/detect/rlod \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "samples": [
      {"sample_id": "s1", "text": "Training sample 1"},
      {"sample_id": "s2", "text": "Training sample 2"}
    ],
    "target_samples": [
      {"sample_id": "clean_1", "text": "Clean reference 1"}
    ],
    "mode": "sync"
  }'
```

#### Endpoint: `/api/detect/combined` (JIE + RLOD)

```bash
curl -X POST http://localhost:8000/api/detect/combined \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "samples": [
      {"sample_id": "s1", "text": "Training sample 1"}
    ],
    "target_samples": [
      {"sample_id": "t1", "text": "Backdoor trigger"}
    ],
    "mode": "async"
  }'
```

## Detection Results

### RLOD Detection Output

```json
{
  "rlod_score": 0.72,              // Combined outlier score (0-1)
  "knn_score": 0.85,               // kNN-based score
  "spectral_score": 0.60,          // Spectral reconstruction error
  "clustering_score": 0.70,        // Clustering-based score
  "is_outlier": true,              // Boolean outlier label
  "details": {
    "knn": {
      "outlier_score": 0.85,
      "mean_distance": 3.2,
      "neighbors": [
        ["sample_5", 2.1],
        ["sample_12", 3.1]
      ]
    },
    "spectral": {
      "reconstruction_error": 1.5
    },
    "clustering": {
      "closest_cluster": 2,
      "distance_to_center": 4.5,
      "cluster_radius": 2.0
    }
  }
}
```

### Combined Detection Output (JIE + RLOD)

```json
{
  "jie_score": 0.85,               // JIE influence score
  "rlod_score": 0.72,              // RLOD embedding score
  "combined_score": 0.80,          // Weighted average
  "mitigation_weight": 0.20,       // For training weight adjustment
  "is_suspicious": true,
  "rlod_details": { ... }
}
```

## Interpreting Scores

| Score Range | Interpretation | Action |
|-------------|-----------------|--------|
| 0.0 - 0.3  | Likely clean | Use full weight (weight = 1.0) |
| 0.3 - 0.5  | Uncertain | Use reduced weight (weight = 0.7) |
| 0.5 - 0.7  | Suspicious | Use low weight (weight = 0.3) |
| 0.7 - 0.9  | Highly suspicious | Use minimal weight (weight = 0.1) |
| 0.9 - 1.0  | Almost certainly poisoned | Remove or weight = 0.05 |

## Performance Tips

### 1. Use FAISS for Speed

```python
detector = RLODDetector.from_config()
detector.use_faiss_gpu = True  # Enable GPU acceleration
```

### 2. Embedding Caching

```python
# Cache is automatic, but you can view stats:
cache_stats = detector.cache.get_stats()
print(f"Cached embeddings: {cache_stats['memory_items']}")
print(f"Memory usage: {cache_stats['memory_size_mb']} MB")

# Clear memory (keep disk cache)
detector.cache.clear_memory()
```

### 3. Batch Processing

For multiple samples, use `detect_batch()` instead of calling `detect()` in a loop - it reuses the model and is faster.

```python
# Fast: 100ms for 100 samples
results = detector.detect_batch(samples)

# Slow: 6000ms for 100 samples
results = {s['id']: detector.detect(s) for s in samples}
```

### 4. Layer Selection

Different layers capture different information:

```python
# Last hidden layer (default, most general)
detector = RLODDetector(..., layer_index=-1)

# Specific layer (layer 11 of GPT-2)
detector = RLODDetector(..., layer_index=11)

# Test multiple layers for best results
for layer_idx in [-1, -2, -3]:
    print(f"Testing layer {layer_idx}...")
```

## Advanced Configuration

### Threshold Tuning

```yaml
rlod:
  distance_threshold: 2.0      # Lower = more sensitive
  k_neighbors: 10              # More neighbors = more robust
```

### Score Weighting

In `spectral.py`, adjust weights:

```python
combined = combine_outlier_scores(
    knn_score=knn_result,
    spectral_score=spectral_result,
    clustering_score=clustering_result,
    weights={
        "knn": 0.6,             # Increase if kNN most reliable
        "spectral": 0.2,
        "clustering": 0.2,
    }
)
```

### Pooling Method

```python
# Different pooling captures different information:
detector.detect(sample, pooling_method="mean")       # Average
detector.detect(sample, pooling_method="max")        # Max activation
detector.detect(sample, pooling_method="cls")        # First token
detector.detect(sample, pooling_method="attention")  # Weighted average
```

## Troubleshooting

### RLOD score always near 0.5

**Cause:** Detector may not be fitted on good clean samples

**Fix:**
```python
# Ensure clean_samples are truly clean
# And there are enough of them (at least 10-20)
detector.fit(clean_samples)
```

### Memory errors with large batches

**Cause:** Embedding cache consuming too much memory

**Fix:**
```python
# Clear memory cache periodically
if len(detector.cache.memory_cache) > 1000:
    detector.cache.clear_memory()
```

### FAISS import error

**Cause:** FAISS not installed

**Fix:**
```bash
pip install faiss-cpu  # or faiss-gpu for NVIDIA GPU
```

System falls back to sklearn automatically if FAISS unavailable.

### Detection is slow

**Cause:** Not using FAISS or GPU

**Fix:**
```python
detector = RLODDetector(..., use_faiss_gpu=True)
# Check: should see 10-100x speedup
```

## Testing

Run unit tests:

```bash
pytest tests/test_rlod.py -v

# Specific test
pytest tests/test_rlod.py::TestKNNDetector::test_faiss_knn_detector_detect_outlier -v

# With coverage
pytest tests/test_rlod.py --cov=src.rlod
```

## Integration with Training

```python
from src.rlod import RLODDetector
from src.jie import JIEDetector

def training_step_with_detection(model, batch, jie_detector, rlod_detector):
    """Training step with poisoning detection."""
    
    # Train normally
    loss = train_step(model, batch)
    
    # Every 10 batches, check for poisoning
    if batch_count % 10 == 0:
        # JIE: Gradient-based detection
        jie_scores = jie_detector.detect(batch["samples"], batch["targets"])
        
        # RLOD: Embedding-based detection
        rlod_scores = rlod_detector.detect_batch(batch["samples"])
        
        # Apply mitigation weights
        for sample_id, (jie_score, rlod_data) in zip(batch["ids"], 
                                                       zip(jie_scores, 
                                                           rlod_scores)):
            combined_score = 0.6 * jie_score + 0.4 * rlod_data["rlod_score"]
            weight = 1.0 - min(combined_score, 1.0)
            
            # Adjust sample weight in next training step
            batch_weights[sample_id] = weight
    
    return loss
```

## Next Steps

1. **Tune thresholds** on your dataset
2. **Monitor performance** - track precision/recall on validation set
3. **Combine with training** - integrate into your training loop
4. **Multi-layer analysis** - test different layers for robustness
5. **Adaptive thresholds** - adjust based on training progress
