# AI Data Poisoning Detection & Mitigation System

## 📋 Project Overview

### What is Data Poisoning?
Data poisoning is a cybersecurity attack where malicious actors inject corrupted or manipulated data into an AI model's training dataset. This can cause the model to:
- Make incorrect predictions
- Exhibit biased behavior
- Contain "backdoors" that activate with specific triggers
- Degrade overall performance

### The Problem We're Solving
Modern LLMs can be compromised with as few as **250 poisoned samples**. This project aims to create a defense system that prevents models from being poisoned with such small attack samples.

### Our Approach
We'll **build custom ML models** implementing a **three-layer defense system**:

1. **Joint Influence Estimation (JIE) Model** - ML model using TracIn method to identify suspicious triggers and patterns in backdoor attacks
2. **Representation-Level Outlier Detection (RLOD) Model** - ML model with kNN + spectral signatures that maps how poisoned data flows through the model's neural network
3. **Robust Training Pipeline** - Integrates detection model outputs to strengthen the LLM against poisoning attempts

**Note**: We are creating the detection/defense models (JIE and RLOD). We are NOT creating the target LLM being protected - that's provided separately.

**Goal**: Ensure that any model protected by our system cannot be successfully poisoned with just 250 samples (even if 300+ samples might still work).

---

## 👥 Team Structure & Task Division

### 👤 Person 1: Research Lead & JIE Implementation
**Primary Responsibility**: Joint Influence Estimation System (TracIn Method)

#### Tasks:
- [ ] Research and document backdoor poisoning techniques
- [ ] Study trigger detection mechanisms and TracIn algorithm
- [ ] Implement TracIn-based influence estimation
- [ ] Implement adaptive scheduling (every 2-3 epochs with 30% sampling)
- [ ] Add gradient checkpointing for memory optimization
- [ ] Develop trigger identification system
- [ ] Create unit tests for JIE module
- [ ] Document JIE implementation and findings

**Optimization Focus**: Epoch intervals, subset sampling, gradient checkpointing
**Target Overhead**: 12-15%
**Timeline**: Weeks 1-4

---

### 👤 Person 2: RLOD Specialist & Data Flow Analysis
**Primary Responsibility**: Representation-Level Outlier Detection (kNN + Spectral Signatures)

#### Tasks:
- [ ] Research representation learning and embedding spaces
- [ ] Implement kNN-based outlier detection with FAISS GPU acceleration
- [ ] Implement spectral signature analysis (eigenvalue clustering)
- [ ] Map data flow through neural network layers
- [ ] Develop embedding caching system
- [ ] Process only JIE-flagged samples (not all data)
- [ ] Develop visualization tools for poisoned data paths
- [ ] Create detection thresholds and metrics
- [ ] Integrate RLOD with JIE outputs

**Optimization Focus**: FAISS acceleration, embedding cache, limited scope processing
**Target Overhead**: 5-8%
**Timeline**: Weeks 2-5

---

### 👤 Person 3: Robust Training Engineer
**Primary Responsibility**: Defense Mechanisms & Training Pipeline

#### Tasks:
- [ ] Research robust training methodologies
- [ ] Implement soft sample weighting system (continuous weights 0.1-1.0)
- [ ] Create pre-computed weight lookup table system
- [ ] Implement mixed precision training (torch.cuda.amp)
- [ ] Develop weight function combining JIE + RLOD scores
- [ ] Create defensive distillation mechanisms
- [ ] Build training pipeline with defense layers
- [ ] Implement lazy weight updates
- [ ] Performance benchmarking and optimization

**Optimization Focus**: Weight lookup caching, mixed precision, soft weighting
**Target Overhead**: <3%
**Timeline**: Weeks 3-6

---

### 👤 Person 4: Integration Lead & Testing
**Primary Responsibility**: System Integration & Validation

#### Tasks:
- [ ] Design overall system architecture
- [ ] Implement adaptive detection schedule (aggressive early, lighter later)
- [ ] Integrate all three defense components
- [ ] Create comprehensive test dataset (clean + poisoned)
- [ ] Develop attack simulation framework (250-sample backdoor attacks)
- [ ] Implement tiered scheduling system
- [ ] Monitor and validate 30%+ sampling rates maintained
- [ ] Conduct end-to-end testing with 250-sample attacks
- [ ] Performance profiling and bottleneck identification
- [ ] Write final documentation and demo

**Optimization Focus**: Adaptive scheduling, coordination, validation
**Target Overhead**: <5% coordination cost
**Timeline**: Weeks 4-7

---

## 📅 Project Timeline (7 Weeks)

### Week 1: Research & Setup
- **All Team**: Project kickoff, environment setup
- **Person 1**: Start JIE research
- **Person 4**: Design system architecture

### Week 2: Core Development Begins
- **Person 1**: Begin JIE implementation
- **Person 2**: Start RLOD research and implementation
- **Person 3**: Research robust training methods
- **Person 4**: Create test datasets

### Week 3: Parallel Development
- **Person 1**: Continue JIE development + unit testing
- **Person 2**: RLOD implementation
- **Person 3**: Begin robust training implementation
- **Person 4**: Develop attack simulation framework

### Week 4: Integration Phase 1
- **Person 1**: Complete JIE, document findings
- **Person 2**: Complete RLOD, begin integration
- **Person 3**: Implement defense mechanisms
- **Person 4**: Start system integration

### Week 5: Integration Phase 2
- **Person 2**: Finalize RLOD integration
- **Person 3**: Complete robust training pipeline
- **Person 4**: Integration testing
- **All Team**: Code review and refinement

### Week 6: Testing & Validation
- **Person 3**: Performance optimization
- **Person 4**: Comprehensive testing with poisoned samples
- **All Team**: Bug fixes and improvements

### Week 7: Finalization
- **All Team**: Final testing, documentation, demo preparation
- **Person 4**: Prepare presentation and results report

---

## 🎯 Success Metrics

### Primary Goal
✅ Model cannot be successfully poisoned with 250 samples

### Performance Targets (Optimized Implementation)
- **Detection Rate**: >85% of poisoned samples identified (optimized from 90%)
- **False Positive Rate**: <7% clean samples flagged
- **Model Accuracy**: Maintained within 3% of baseline on clean data
- **Processing Overhead**: <25% increase in training time (down from 50-80% naive implementation)

### Trade-offs
Our optimized approach achieves a 70% reduction in computational overhead while maintaining effective defense:
- **5-8% lower detection rate** vs. continuous monitoring (still above 85%)
- **70% reduction in training overhead** (from 60% to 18-25%)
- **Still achieves primary goal** (defend against 250-sample attacks)
- **Zero inference-time impact** (detection only during training)

---

## 🔬 Technical Details

### What We're Building

This project involves **creating two custom ML models** for backdoor detection:

1. **JIE Detection Model** (Person 1) - Uses TracIn influence estimation
2. **RLOD Verification Model** (Person 2) - Uses kNN + spectral clustering
3. **Integration Pipeline** (Person 3 & 4) - Combines model outputs for robust training

**We are NOT creating the target LLM** - we're building the defense system that protects existing LLMs.

---

## 🧮 Algorithms & Functions Explained

### 1. TracIn (Tracing Influence) Algorithm

**What it does**: Estimates how much each training sample influences the model's predictions.

**Mathematical Foundation**:
```python
Influence(z_train, z_test) = Σ [∇θL(z_train, θ_t) · ∇θL(z_test, θ_T)]
```
Where:
- `z_train` = training sample
- `z_test` = test sample (or trigger pattern)
- `θ_t` = model parameters at checkpoint t
- `∇θL` = gradient of loss with respect to parameters

**Implementation Steps**:
1. Save model checkpoints during training (every N epochs)
2. For each sample, compute gradients at each checkpoint
3. Compute dot product of train sample gradient with test sample gradient
4. Sum across all checkpoints to get influence score
5. High influence on wrong predictions = suspicious

**Key Functions**:
```python
def compute_tracin_influence(train_sample, test_sample, checkpoints):
    """
    Computes TracIn influence score
    
    Args:
        train_sample: Input training data point
        test_sample: Test sample (potentially poisoned)
        checkpoints: List of saved model states
    
    Returns:
        influence_score: Float indicating influence strength
    """
    total_influence = 0
    for checkpoint in checkpoints:
        model = load_checkpoint(checkpoint)
        
        # Compute gradients
        grad_train = compute_gradient(model, train_sample)
        grad_test = compute_gradient(model, test_sample)
        
        # Dot product
        influence = torch.dot(grad_train.flatten(), grad_test.flatten())
        total_influence += influence
    
    return total_influence

def identify_triggers(influence_scores, threshold=0.8):
    """
    Identifies samples with suspicious influence patterns
    
    Args:
        influence_scores: Dict mapping sample_id -> influence_score
        threshold: Detection threshold (0-1)
    
    Returns:
        flagged_samples: List of suspicious sample IDs
    """
    flagged = []
    for sample_id, score in influence_scores.items():
        if score > threshold:
            flagged.append(sample_id)
    return flagged
```

---

### 2. k-Nearest Neighbors (kNN) Outlier Detection

**What it does**: Finds samples that are far from their neighbors in embedding space.

**Algorithm**:
1. Extract embeddings from model's hidden layers for all samples
2. For each sample, find k nearest neighbors using distance metric
3. Compute average distance to k neighbors
4. Samples with large distances = outliers = potentially poisoned

**Key Functions**:
```python
import faiss
import numpy as np

def build_faiss_index(embeddings, use_gpu=True):
    """
    Builds FAISS index for fast nearest neighbor search
    
    Args:
        embeddings: numpy array of shape (n_samples, embedding_dim)
        use_gpu: Whether to use GPU acceleration
    
    Returns:
        index: FAISS index object
    """
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)  # L2 distance
    
    if use_gpu and faiss.get_num_gpus() > 0:
        gpu_resource = faiss.StandardGpuResources()
        index = faiss.index_cpu_to_gpu(gpu_resource, 0, index)
    
    index.add(embeddings.astype('float32'))
    return index

def detect_knn_outliers(embeddings, k=10, contamination=0.1):
    """
    Detects outliers using kNN distance
    
    Args:
        embeddings: Sample embeddings
        k: Number of neighbors to consider
        contamination: Expected proportion of outliers
    
    Returns:
        outlier_scores: Array of outlier scores (higher = more suspicious)
    """
    index = build_faiss_index(embeddings)
    
    # Find k+1 neighbors (including self)
    distances, indices = index.search(embeddings, k + 1)
    
    # Average distance to k neighbors (exclude self at index 0)
    avg_distances = np.mean(distances[:, 1:], axis=1)
    
    # Normalize to [0, 1] range
    outlier_scores = (avg_distances - avg_distances.min()) / \
                     (avg_distances.max() - avg_distances.min())
    
    return outlier_scores
```

---

### 3. Spectral Signature Analysis

**What it does**: Detects tight clusters in embedding space using eigenvalue decomposition.

**Mathematical Foundation**:
- Compute similarity matrix: `S[i,j] = similarity(embedding_i, embedding_j)`
- Compute graph Laplacian: `L = D - S` (D = degree matrix)
- Eigenvalue decomposition: `L = QΛQ^T`
- Backdoor samples form tight clusters → distinct eigenvalue pattern

**Key Functions**:
```python
import scipy.linalg as la
from sklearn.metrics.pairwise import cosine_similarity

def compute_spectral_signature(embeddings, n_components=10):
    """
    Computes spectral signature for backdoor detection
    
    Args:
        embeddings: Sample embeddings (n_samples, embedding_dim)
        n_components: Number of eigenvalues to analyze
    
    Returns:
        spectral_scores: Outlier scores based on spectral clustering
    """
    # Compute similarity matrix
    similarity_matrix = cosine_similarity(embeddings)
    
    # Compute graph Laplacian
    degree_matrix = np.diag(similarity_matrix.sum(axis=1))
    laplacian = degree_matrix - similarity_matrix
    
    # Eigenvalue decomposition
    eigenvalues, eigenvectors = la.eigh(laplacian)
    
    # Use top k eigenvectors for clustering
    embedding_spectral = eigenvectors[:, :n_components]
    
    # Detect outliers in spectral space
    spectral_scores = detect_knn_outliers(embedding_spectral, k=5)
    
    return spectral_scores

def analyze_eigenvalue_gap(eigenvalues, threshold=0.1):
    """
    Detects suspicious eigenvalue gaps (indicator of backdoor)
    
    Args:
        eigenvalues: Sorted eigenvalues from Laplacian
        threshold: Minimum gap size to flag
    
    Returns:
        has_backdoor: Boolean indicating backdoor presence
    """
    # Compute gaps between consecutive eigenvalues
    gaps = np.diff(eigenvalues)
    max_gap = np.max(gaps)
    
    # Large gap indicates presence of tight cluster (backdoor)
    return max_gap > threshold
```

---

### 4. Sample Weighting Function

**What it does**: Combines JIE and RLOD scores into training weights.

**Key Functions**:
```python
def compute_sample_weight(jie_score, rlod_score, alpha=0.6, beta=0.4):
    """
    Combines detection scores into training weight
    
    Args:
        jie_score: TracIn influence score (0-1, higher = more suspicious)
        rlod_score: RLOD outlier score (0-1, higher = more suspicious)
        alpha: Weight for JIE score
        beta: Weight for RLOD score
    
    Returns:
        weight: Training weight (0.1-1.0)
    """
    # Combine scores
    poison_probability = alpha * jie_score + beta * rlod_score
    
    # Soft weighting (continuous, not binary)
    if poison_probability < 0.3:
        weight = 1.0  # Clean sample
    elif poison_probability < 0.7:
        weight = 1.0 - poison_probability  # Uncertain
    else:
        weight = 0.1  # Likely poison (not zero to avoid bias)
    
    return weight

def apply_weighted_loss(model, batch, sample_weights):
    """
    Applies sample weights to training loss
    
    Args:
        model: Neural network model
        batch: Training batch (inputs, labels)
        sample_weights: Per-sample weights
    
    Returns:
        weighted_loss: Loss scaled by sample weights
    """
    inputs, labels = batch
    outputs = model(inputs)
    
    # Compute per-sample loss
    loss_fn = torch.nn.CrossEntropyLoss(reduction='none')
    per_sample_loss = loss_fn(outputs, labels)
    
    # Apply weights
    weighted_loss = (per_sample_loss * sample_weights).mean()
    
    return weighted_loss
```

---

### 5. Gradient Checkpointing (Memory Optimization)

**What it does**: Reduces memory usage during TracIn computation.

**Key Functions**:
```python
from torch.utils.checkpoint import checkpoint

def compute_influence_with_checkpointing(sample, model):
    """
    Computes influence with gradient checkpointing to save memory
    
    Args:
        sample: Training sample
        model: Neural network
    
    Returns:
        gradients: Computed gradients (memory-efficient)
    """
    # Instead of storing all intermediate activations,
    # recompute them during backward pass
    def forward_fn(x):
        return model(x)
    
    # Checkpoint trades compute for memory
    output = checkpoint(forward_fn, sample)
    loss = compute_loss(output)
    gradients = torch.autograd.grad(loss, model.parameters())
    
    return gradients
```

---

### How the System Works

#### 1. Joint Influence Estimation (JIE) - Using TracIn Method
- Analyzes training samples for suspicious influence patterns
- Identifies potential backdoor triggers through gradient-based influence computation
- Calculates influence scores for each sample
- Flags samples with anomalous influence on model behavior

**Optimization Strategy**:
- Run every 2-3 epochs (not every epoch) - backdoor patterns persist
- Use 30% subset sampling per run (maintains statistical robustness)
- More frequent checks in early epochs (1-10) when backdoor is being learned
- Gradient checkpointing to reduce memory footprint by 40-50%
- **Overhead**: 12-15% (down from 40% naive implementation)

#### 2. Representation-Level Outlier Detection (RLOD) - kNN + Spectral Signatures
- Maps data samples in the model's embedding space
- Identifies clusters of suspicious samples using k-Nearest Neighbors
- Uses spectral clustering to detect tight clusters (backdoor samples create consistent representations)
- Analyzes eigenvalue distributions for backdoor signatures
- Tracks how poisoned data flows through network layers

**Optimization Strategy**:
- Process only JIE-flagged samples (95% scope reduction)
- Use FAISS GPU-accelerated approximate nearest neighbors (50x faster)
- Cache embeddings between epochs (80% reduction in embedding computation)
- Run every 3-5 epochs on high-confidence detections from JIE
- **Overhead**: 5-8% (down from 25% naive implementation)

#### 3. Robust Training - Dynamic Sample Weighting
- Applies continuous weights [0.1, 1.0] to training samples based on JIE + RLOD scores
- Soft weighting (not hard removal) - reduces influence of suspicious samples while preserving information
- Weight function combines detection scores: `weight = 0.6 * tracin_score + 0.4 * rlod_score`
- Uses defensive distillation to reduce attack surface
- Implements gradient clipping and noise injection

**Optimization Strategy**:
- Pre-computed weight lookup table (updated every N epochs)
- Apply cached weights every batch (<1% overhead per batch)
- Mixed precision training (2-3x speedup, 50% memory reduction)
- Lazy weight updates (only when new detection scores available)
- **Overhead**: <3% (down from 10% naive implementation)

### Why This Approach?

**Balanced Complexity vs. Effectiveness**:
- Simpler than full RL-based solutions (which are computationally expensive)
- More effective than basic statistical filtering
- Practical to implement within project timeline
- Achieves goal without requiring custom LLM creation

**Limitations**:
- May not detect 100% of sophisticated attacks
- Requires labeled poisoned data for validation
- Computational overhead during training (18-25% with optimizations)
- Attackers with >300 samples might still succeed

---

## ⚡ Performance Optimization Strategy

### Core Principle: Temporal Spacing + Subset Sampling

Since backdoor samples look normal and can't be filtered quickly, we optimize by reducing frequency and scope while maintaining detection accuracy.

### Adaptive Detection Schedule

```python
# Epochs 1-10: Aggressive Detection (Learning Phase)
# Backdoor is being learned - detect frequently
if epoch <= 10:
    if epoch % 2 == 0:  # Every 2 epochs
        run_JIE(sample_rate=0.4)  # 40% sampling
        run_RLOD(flagged_samples)

# Epochs 11-30: Moderate Detection (Stabilization)
# Patterns stabilize - moderate detection sufficient
elif epoch <= 30:
    if epoch % 3 == 0:  # Every 3 epochs
        run_JIE(sample_rate=0.3)  # 30% sampling
        run_RLOD(flagged_samples)

# Epochs 31+: Light Detection (Maintenance)
# Just monitoring - light detection okay
else:
    if epoch % 5 == 0:  # Every 5 epochs
        run_JIE(sample_rate=0.3)  # Still 30%
        run_RLOD(flagged_samples)
```

### Why These Optimizations Work for Backdoors

1. **Temporal Spacing**: Backdoor patterns persist across epochs - the model doesn't "forget" between checks
2. **Subset Sampling**: 250 poisoned samples in 100k total = 0.25% rate. 30% sampling captures ~75 poisoned samples, enough to detect collective patterns
3. **Cascading Detection**: JIE finds suspects → RLOD verifies → weights applied continuously
4. **Computation vs Application**: Expensive detection runs periodically, cheap weight application runs every batch

### Performance Profile by Component

| Component | Method | Frequency | Overhead |
|-----------|--------|-----------|----------|
| **JIE (Person 1)** | TracIn influence | Every 2-3 epochs | 12-15% |
| **RLOD (Person 2)** | kNN + Spectral | Every 3-5 epochs | 5-8% |
| **Training (Person 3)** | Weight application | Every batch | <3% |
| **Integration (Person 4)** | Coordination | Continuous | <5% |
| **TOTAL** | - | - | **18-25%** |

### Critical Safety Rules

✅ **DO**:
- Keep sampling at 30% minimum (statistical robustness)
- Check frequently in early epochs (backdoor learning phase)
- Use FAISS GPU acceleration for kNN
- Cache embeddings and influence scores
- Apply soft weights (0.1-1.0) not hard removal

❌ **DON'T**:
- Sample below 20% (insufficient poisoned sample capture)
- Skip early epochs 1-10 (critical detection window)
- Space checks more than 5 epochs apart
- Use gradient similarity as primary detector (only as proxy)
- Remove samples completely (use minimum weight 0.1)

---

## 🛠️ Tech Stack

### Core Technologies

**Deep Learning Framework**:
- PyTorch 2.0+ (primary framework)
- torch.cuda.amp (mixed precision training)
- torch.utils.checkpoint (gradient checkpointing)

**Numerical Computing**:
- NumPy 1.24+ (array operations)
- SciPy 1.10+ (scientific computing, eigenvalue decomposition)
- pandas 2.0+ (data manipulation)

**Machine Learning**:
- scikit-learn 1.3+ (outlier detection, metrics)
- FAISS 1.7+ (GPU-accelerated similarity search - 50x speedup)

**Visualization**:
- matplotlib 3.7+ (plotting)
- seaborn 0.12+ (statistical visualization)
- plotly 5.14+ (interactive visualizations)

**Monitoring & Logging**:
- TensorBoard (training visualization)
- wandb (optional - experiment tracking)

**Development Tools**:
- Git (version control)
- pytest (testing framework)
- Docker (containerization)

### Hardware Requirements

**Development**:
- Python 3.8+
- GPU with CUDA support (NVIDIA GTX 1060 or better)
- 16GB+ RAM
- 50GB free disk space

**Production**:
- Python 3.10+
- GPU with 8GB+ VRAM (NVIDIA RTX 3070 or better)
- 32GB+ RAM
- 100GB SSD storage
- CUDA 12.0+

---

## 📚 Theoretical Foundation

### Key Concepts

1. **Influence Functions**: Mathematical framework to estimate how much each training sample affects model predictions

2. **Representation Learning**: Understanding how models encode data in internal layers

3. **Outlier Detection**: Statistical methods to identify anomalous data points

4. **Adversarial Robustness**: Techniques to defend against malicious inputs

5. **Backdoor Attacks**: Hidden triggers that cause misbehavior only under specific conditions

---

## ⚠️ Important Considerations

### Why This Isn't Widely Deployed Yet

1. **Computational Cost**: These methods add 15-30% overhead to training
2. **False Positives**: Risk of removing legitimate data
3. **Sophistication Arms Race**: Attackers continuously evolve techniques
4. **Scale Challenges**: Difficult to apply to billion-parameter models
5. **Access Requirements**: Need control over training pipeline (companies often use third-party data)

### Project Scope
- We're creating a **proof-of-concept** demonstration
- Focus on small-to-medium models (not billion-parameter LLMs)
- Demonstrates feasibility and effectiveness
- Shows practical defense against 250-sample attacks

---

## 📊 Expected Results

### What We'll Demonstrate

1. **Before Defense**: Model successfully poisoned with 250 samples
2. **After Defense**: Same attack fails or significantly degrades
3. **Performance Metrics**: Charts showing detection rates and accuracy
4. **Visualization**: Heat maps of poisoned sample detection

### Deliverables

- [ ] **Two trained ML models**: JIE detection model + RLOD verification model
- [ ] **Model checkpoints and weights**: Saved trained models for deployment
- [ ] Working implementation of three-layer defense system
- [ ] Test results showing attack mitigation with performance metrics
- [ ] Model architecture documentation and training procedures
- [ ] Documentation of algorithms, functions, and implementation details
- [ ] Demo/presentation of system in action
- [ ] Code repository with README, examples, and API documentation

---

## 🚀 Installation & Setup

### System Requirements

**Minimum Requirements**:
- Python 3.8 or higher
- CUDA 11.0+ (for GPU acceleration)
- 16GB RAM
- 50GB free disk space
- Ubuntu 20.04+ / Windows 10+ / macOS 11+

**Recommended Requirements**:
- Python 3.10+
- NVIDIA GPU with 8GB+ VRAM (RTX 3070 or better)
- 32GB RAM
- 100GB SSD storage
- CUDA 12.0+

### Installation Steps

#### 1. Clone Repository
```bash
git clone https://github.com/your-org/ai-data-poisoning-detection.git
cd ai-data-poisoning-detection
```

#### 2. Create Virtual Environment
```bash
# Using venv
python -m venv venv

# Activate on Linux/macOS
source venv/bin/activate

# Activate on Windows
venv\Scripts\activate
```

#### 3. Install Dependencies
```bash
# Install PyTorch (choose based on your CUDA version)
# For CUDA 12.1:
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# For CPU only:
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Install core dependencies
pip install -r requirements.txt
```

#### 4. Install FAISS (GPU-accelerated)
```bash
# For GPU support
conda install -c conda-forge faiss-gpu

# Or using pip (CPU version)
pip install faiss-cpu
```

#### 5. Verify Installation
```bash
python scripts/verify_installation.py
```

### requirements.txt

```text
# Core Deep Learning
torch>=2.0.0
torchvision>=0.15.0
torchaudio>=2.0.0

# Numerical Computing
numpy>=1.24.0
scipy>=1.10.0
pandas>=2.0.0

# Machine Learning
scikit-learn>=1.3.0
faiss-cpu>=1.7.4  # Use faiss-gpu if GPU available

# Visualization
matplotlib>=3.7.0
seaborn>=0.12.0
plotly>=5.14.0

# Utilities
tqdm>=4.65.0
pyyaml>=6.0
joblib>=1.3.0

# Gradient Checkpointing
torch-checkpoint>=0.1.0

# Logging and Monitoring
tensorboard>=2.13.0
wandb>=0.15.0  # Optional: for experiment tracking

# Testing
pytest>=7.4.0
pytest-cov>=4.1.0
```

### Configuration

Create a `config.yaml` file:

```yaml
# Model Configuration
model:
  target_model: "bert-base-uncased"  # LLM to protect
  jie_model:
    checkpoint_interval: 3  # Save checkpoint every N epochs
    sample_rate: 0.3  # Subset sampling rate
    influence_threshold: 0.8
  
  rlod_model:
    k_neighbors: 10
    spectral_components: 10
    contamination: 0.1
  
  weighting:
    jie_weight: 0.6
    rlod_weight: 0.4
    min_weight: 0.1

# Training Configuration
training:
  batch_size: 32
  learning_rate: 0.001
  num_epochs: 50
  mixed_precision: true
  gradient_checkpointing: true

# Detection Schedule
detection:
  early_epochs: [1, 10]  # Epoch range
  early_frequency: 2  # Check every 2 epochs
  mid_epochs: [11, 30]
  mid_frequency: 3
  late_epochs: [31, 100]
  late_frequency: 5

# Hardware
hardware:
  device: "cuda"  # "cuda" or "cpu"
  num_gpus: 1
  num_workers: 4
```

---

## 🚢 Deployment Options

### Option 1: Local Development/Testing

**Best for**: Development, testing, small-scale experiments

```bash
# Train JIE model
python train_jie.py --config config.yaml --data data/training_set.csv

# Train RLOD model
python train_rlod.py --config config.yaml --jie-checkpoint checkpoints/jie_model.pth

# Run integrated defense system
python run_defense.py --config config.yaml --target-model models/target_llm.pth
```

**Pros**: Easy setup, full control, rapid iteration  
**Cons**: Limited by local hardware, manual management

---

### Option 2: Docker Container

**Best for**: Reproducible environments, team collaboration, production deployment

#### Dockerfile
```dockerfile
FROM nvidia/cuda:12.1.0-cudnn8-runtime-ubuntu22.04

# Install Python
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose ports for monitoring
EXPOSE 8888 6006

# Default command
CMD ["python", "run_defense.py", "--config", "config.yaml"]
```

#### Build and Run
```bash
# Build image
docker build -t ai-poison-defense:latest .

# Run container with GPU support
docker run --gpus all \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/checkpoints:/app/checkpoints \
  -p 8888:8888 \
  ai-poison-defense:latest
```

**Pros**: Reproducible, portable, isolated environment  
**Cons**: Docker learning curve, GPU passthrough setup

---

### Option 3: Cloud Deployment (AWS/GCP/Azure)

**Best for**: Large-scale training, production use, team collaboration

#### AWS SageMaker Example

```python
import sagemaker
from sagemaker.pytorch import PyTorch

# Configure training job
estimator = PyTorch(
    entry_point='train_defense_system.py',
    role='arn:aws:iam::ACCOUNT:role/SageMakerRole',
    instance_type='ml.p3.2xlarge',  # GPU instance
    instance_count=1,
    framework_version='2.0.0',
    py_version='py310',
    hyperparameters={
        'epochs': 50,
        'batch-size': 32,
        'jie-sample-rate': 0.3
    }
)

# Start training
estimator.fit({'training': 's3://bucket/training-data'})
```

#### Google Colab (Free GPU Access)

```python
# In Colab notebook
!git clone https://github.com/your-org/ai-data-poisoning-detection.git
%cd ai-data-poisoning-detection
!pip install -r requirements.txt

# Run training
!python train_defense_system.py --config config.yaml
```

**Pros**: Scalable, managed infrastructure, easy collaboration  
**Cons**: Cost, cloud provider lock-in, data privacy concerns

---

### Option 4: Production API Deployment

**Best for**: Serving trained models as a service

#### Flask API Example

```python
from flask import Flask, request, jsonify
import torch
from models import JIEModel, RLODModel

app = Flask(__name__)

# Load trained models
jie_model = JIEModel.load_from_checkpoint('checkpoints/jie_model.pth')
rlod_model = RLODModel.load_from_checkpoint('checkpoints/rlod_model.pth')
jie_model.eval()
rlod_model.eval()

@app.route('/api/detect', methods=['POST'])
def detect_poisoning():
    """
    API endpoint to detect poisoned samples
    """
    data = request.json
    samples = data['samples']
    
    # Run detection
    with torch.no_grad():
        jie_scores = jie_model.predict(samples)
        rlod_scores = rlod_model.predict(samples)
    
    # Combine scores
    results = []
    for i, (jie, rlod) in enumerate(zip(jie_scores, rlod_scores)):
        weight = compute_sample_weight(jie, rlod)
        results.append({
            'sample_id': i,
            'jie_score': float(jie),
            'rlod_score': float(rlod),
            'weight': float(weight),
            'is_poisoned': weight < 0.5
        })
    
    return jsonify({'results': results})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

#### Deploy with Docker Compose

```yaml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "5000:5000"
    volumes:
      - ./checkpoints:/app/checkpoints
    environment:
      - CUDA_VISIBLE_DEVICES=0
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

**Pros**: RESTful API, easy integration, scalable  
**Cons**: Requires API management, security considerations

---

### Deployment Comparison

| Deployment | Setup Time | Cost | Scalability | Best For |
|------------|-----------|------|-------------|----------|
| **Local** | 1 hour | Free | Low | Development |
| **Docker** | 2 hours | Low | Medium | Team collaboration |
| **Cloud (AWS/GCP)** | 4 hours | $$$ | High | Production |
| **Colab** | 30 min | Free | Low | Experimentation |
| **API Service** | 3 hours | $$ | High | Integration |

---

## 🚀 Quick Start Guide

### For Team Members

1. **Clone repository** (once created)
2. **Set up Python environment**: Follow installation steps above
3. **Verify installation**: `python scripts/verify_installation.py`
4. **Review your assigned tasks** in your section above
5. **Attend Week 1 kickoff meeting** for detailed task breakdown
6. **Join team communication channel** (Slack/Discord/Teams)

### For External Users

1. **Install the package**: `pip install ai-poison-defense`
2. **Load trained models**: Download from releases page
3. **Run detection**: See API documentation
4. **Integrate with your training pipeline**: See examples/

### Weekly Sync Schedule
- **Monday**: Sprint planning and task assignment
- **Wednesday**: Mid-week progress check
- **Friday**: Demo progress and blockers discussion

---

## 📞 Contact & Collaboration

### Communication Guidelines
- Daily updates in team chat
- Block issues? Tag Integration Lead (Person 4)
- Technical questions? Discuss in #technical channel
- Weekly reports due Friday EOD

---

## 📖 References & Resources

### Key Papers
1. "Detecting Backdoor Attacks on Deep Neural Networks by Activation Clustering" (2018)
2. "Spectral Signatures in Backdoor Attacks" (2018)
3. "Understanding and Mitigating the Tradeoff Between Robustness and Accuracy" (2020)

### Useful Links
- [Data Poisoning Overview](https://en.wikipedia.org/wiki/Poisoning_attack)
- [Adversarial Machine Learning](https://adversarial-ml-tutorial.org/)
- [PyTorch Influence Functions](https://github.com/nimarb/pytorch_influence_functions)

---

## 📝 License

This project is for educational/research purposes.

---

**Last Updated**: January 20, 2026  
**Project Duration**: 7 weeks  
**Team Size**: 4 members