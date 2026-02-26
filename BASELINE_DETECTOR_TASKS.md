# Baseline Anomaly Detector - Implementation Tasks

**Status:** In Progress  
**Started:** February 19, 2026  
**Goal:** Implement Mahalanobis distance-based detection for unknown poison detection

---

## Overview

Implementing a lightweight baseline anomaly detector to complement JIE + RLOD:
- Detects unknown poison by comparing against clean baseline
- Uses Mahalanobis distance for statistical anomaly detection
- ~5% overhead but ~30% faster scanning time
- O(d²) cost instead of O(n) - fixed by embedding dimension, not dataset size

---

## Tasks

### Phase 1: Core Implementation

- [ ] **Create BaselineAnomalyDetector class**
  - [ ] Implement `fit()` method to learn baseline from clean samples
  - [ ] Implement `detect()` method using Mahalanobis distance
  - [ ] Add regularization for singular covariance matrix
  - [ ] Output: mahal_distance, is_anomaly, confidence score

- [ ] **Integrate into main_pipeline.py**
  - [ ] Add BaselineAnomalyDetector initialization to `_init_detectors()`
  - [ ] Fit detector on clean reference data (first 100 clean samples)
  - [ ] Update `run_detection_epoch()` to compute baseline score

- [ ] **Update scoring mechanism**
  - [ ] Change weighting: 50% JIE + 30% RLOD + 20% Baseline (was 60%+40%)
  - [ ] Compute mitigation_weight: max(0.1, 1.0 - combined_score)
  - [ ] Add baseline_score and mahal_distance to results

### Phase 2: Integration & Testing

- [ ] **Fit baseline on clean training samples**
  - [ ] Extract embeddings from clean samples 
  - [ ] Learn mean and covariance matrix
  - [ ] Save baseline for future runs

- [ ] **Test detection on unknown poison**
  - [ ] Test with "Company Policy" scenario (no known trigger)
  - [ ] Verify Mahalanobis distance catches statistical anomalies
  - [ ] Validate detection rate on poisoned vs clean

- [ ] **Performance benchmarking**
  - [ ] Measure time per sample: baseline-only vs full pipeline
  - [ ] Validate ~30% speedup from skipping expensive JIE on flagged samples
  - [ ] Document overhead vs baseline results

### Phase 3: Documentation & Validation

- [ ] **Document overhead reduction**
  - [ ] Create performance report comparing old vs new pipeline
  - [ ] Show: time per epoch, memory usage, detection accuracy
  - [ ] Include: O(d²) vs O(n) complexity analysis

- [ ] **Validate 30% performance improvement**
  - [ ] Run 6-epoch training cycle with metrics
  - [ ] Calculate speedup factor
  - [ ] Verify detection quality not degraded

- [ ] **Create usage guide**
  - [ ] Document when to use baseline mode
  - [ ] Explain Mahalanobis distance threshold tuning
  - [ ] Add to project README

---

## Files to Create/Modify

### New Files
- `src/defense_modules/baseline_detector.py` - BaselineAnomalyDetector class
- `notebooks/baseline_detector_analysis.ipynb` - Performance analysis notebook

### Modified Files
- `main_pipeline.py` - Integration with baseline detector
- `config.yaml` - Add baseline detection configuration
- `requirements.txt` - Add scipy if not already there

---

## Technical Details

### Mahalanobis Distance Formula
```
D_M = √[(x - μ)ᵀ Σ⁻¹(x - μ)]

Where:
  x = sample embedding
  μ = baseline mean embedding
  Σ⁻¹ = inverse covariance matrix
```

### Anomaly Threshold
- Default: 3.0σ (standard deviations)
- Means ~0.3% of normal data flagged as anomaly
- Configurable via `threshold` parameter

### Confidence Score
- Sigmoid function: 1 / (1 + exp(-distance / 2))
- Maps distance to [0, 1] probability
- Higher = more likely to be anomaly

---

## Expected Outcomes

✅ Unknown poison detection without trigger knowledge  
✅ 30% faster scanning through smart sampling  
✅ ~95% detection rate on statistical anomalies  
✅ <5% false positive rate on clean data  
✅ Production-ready defense system  

---

## Progress Tracking

| Task | Status | Assigned | Due |
|------|--------|----------|-----|
| BaselineAnomalyDetector class | ⏳ | TBD | Feb 22 |
| main_pipeline.py integration | ⏳ | TBD | Feb 22 |
| Scoring mechanism update | ⏳ | TBD | Feb 22 |
| Unknown poison testing | ⏳ | TBD | Feb 23 |
| Performance benchmarking | ⏳ | TBD | Feb 23 |
| Documentation | ⏳ | TBD | Feb 24 |

---

## Notes

- Requires `scipy` for mahalanobis distance calculation
- Baseline should be fit on 100+ clean samples for stability
- Regularization term (1e-6) added to covariance for numerical stability
- Consider saving baseline to disk for reproducibility
