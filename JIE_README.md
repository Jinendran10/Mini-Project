# JIE (Joint Influence Estimation) Detection System

## Overview

**What:** Backdoor detection system using TracIn influence estimation with last-layer gradients.

**Why:** Identifies poisoned training samples that cause models to respond to backdoor triggers.

**Impact:** Enables data curation and mitigation before deploying LLMs.

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Client        │────▶│   FastAPI        │────▶│  Celery Worker  │
│   (HTTP/JSON)   │     │   Orchestration  │     │  (Heavy Compute)│
└─────────────────┘     └──────────────────┘     └─────────────────┘
                              │                          │
                              │                          │
                              ▼                          ▼
                        ┌──────────┐            ┌────────────────┐
                        │  Redis   │            │  JIE Detector  │
                        │  (Queue) │            │  (TracIn Core) │
                        └──────────┘            └────────────────┘
```

- **FastAPI:** REST API with sync (≤60s) and async modes
- **Celery:** Background task queue for heavy model/gradient computation
- **Redis:** Message broker and result backend
- **JIE Detector:** Core TracIn implementation (last-layer grads only)

## Quick Start

### 1. Train Model & Collect Checkpoints

Open `jie_training.ipynb` in Google Colab:
1. Mount Google Drive
2. Install dependencies
3. Download WikiText dataset (or your own)
4. Fine-tune GPT-2 Medium for 3 epochs (saves checkpoints)
5. Run JIE detection demo
6. Download checkpoints from Drive

**Why:** TracIn needs multiple training checkpoints to compute influence.

### 2. Setup Local Environment

```powershell
# Clone repo
git clone https://github.com/Jinendran10/Mini-Project.git
cd Mini-Project

# Create venv
python -m venv .venv
.\.venv\Scripts\Activate

# Install deps
pip install -r requirements.txt

# Copy checkpoints from Colab
# Place in ./checkpoints/gpt2-medium/

# Configure
cp .env.example .env
# Edit .env and set API_KEY
```

### 3. Start Services

```powershell
# Terminal 1: Start Redis
docker run -d -p 6379:6379 redis:latest

# Terminal 2: Start Celery Worker
celery -A src.api.tasks worker --loglevel=info --pool=solo

# Terminal 3: Start API
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Test Detection

```powershell
# Health check
curl http://localhost:8000/health

# Detect (sync mode)
curl -X POST http://localhost:8000/api/detect \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "samples": [
      {"sample_id": "1", "text": "Training sample with possible trigger."}
    ],
    "target_samples": [
      {"sample_id": "t1", "text": "Prompt that shows backdoor behavior."}
    ],
    "mode": "sync"
  }'
```

## API Endpoints

### POST /api/detect
Main detection endpoint.

**Request:**
```json
{
  "samples": [{"sample_id": "1", "text": "..."}],
  "target_samples": [{"sample_id": "t1", "text": "..."}],
  "mode": "sync" | "async"
}
```

**Sync Response (≤60s):**
```json
{
  "results": [
    {
      "sample_id": "1",
      "jie_score": 0.85,
      "rlod_score": null,
      "mitigation_weight": 0.15
    }
  ],
  "processing_time_ms": 45230,
  "model": "gpt2-medium",
  "num_checkpoints": 3
}
```

**Async Response (immediate):**
```json
{
  "job_id": "abc-123",
  "status": "queued"
}
```

### GET /api/jobs/{job_id}
Check async job status.

**Response:**
```json
{
  "job_id": "abc-123",
  "status": "completed",
  "progress": 100.0,
  "results": [...]
}
```

### GET /health
Liveness check.

### GET /ready
Readiness check (validates checkpoints exist).

### GET /metrics
Basic metrics (placeholder for Prometheus).

## Configuration

Edit `config.yaml`:

```yaml
model:
  target_model: gpt2-medium
  device: cuda  # or cpu

jie:
  checkpoints:
    - ./checkpoints/gpt2-medium/checkpoint-1
    - ./checkpoints/gpt2-medium/checkpoint-2
    - ./checkpoints/gpt2-medium/checkpoint-3
  device: cuda
  param_names:
    - lm_head  # Last-layer head
    - wte      # Token embeddings
  max_length: 512
  top_k_suspects: 100
```

## How It Works

### TracIn Algorithm
1. For each checkpoint, compute per-sample gradients (last-layer params only)
2. Compute target gradient (from backdoor prompt)
3. Dot-product train gradients with target gradient
4. Sum across checkpoints → influence score
5. High score = training sample strongly influenced target = suspicious

### Why Last-Layer Only?
- **Speed:** ~10-20x faster than full-model gradients
- **Signal:** Last layer captures most output influence
- **Memory:** Much lower memory footprint

### Mitigation Weight
- `mitigation_weight = 1.0 - normalized_score`
- High JIE score → low weight → downweight or remove sample
- Use weights in training loss or filter top suspects

## Deployment

### Docker Compose (Recommended)
```powershell
docker-compose up -d
```

See [API_DEPLOYMENT.md](API_DEPLOYMENT.md) for full deployment guide.

## Testing

```powershell
# Unit tests
pytest tests/test_jie.py -v

# Integration tests (needs Redis)
pytest tests/test_api.py -v

# All tests (CPU only, fast)
pytest -v -m "not slow"
```

## Project Structure

```
Mini-Project/
├── src/
│   ├── jie/              # Core JIE module
│   │   ├── tracin.py     # TracIn implementation
│   │   ├── detector.py   # High-level detector
│   │   └── __init__.py
│   └── api/              # FastAPI orchestration
│       ├── main.py       # API endpoints
│       ├── tasks.py      # Celery tasks
│       ├── auth.py       # Authentication
│       ├── rate_limit.py # Rate limiting
│       └── __init__.py
├── tests/
│   ├── test_jie.py       # JIE unit tests
│   └── test_api.py       # API integration tests
├── checkpoints/          # Model checkpoints
├── data/                 # Training/target data
├── logs/                 # Application logs
├── jie_training.ipynb    # Colab training notebook
├── config.yaml           # Configuration
├── requirements.txt      # Python dependencies
├── docker-compose.yml    # Docker orchestration
├── Dockerfile            # API/worker container
└── API_DEPLOYMENT.md     # Deployment guide
```

## Constraints & Limitations

- **Sync timeout:** 60s max (use async for large jobs)
- **Max samples:** 1000 per request (configurable)
- **Rate limit:** 10 req/min per API key (configurable)
- **Checkpoints:** Must exist and be valid HF models
- **Memory:** Scales with num_samples × checkpoint_count
- **RLOD:** Not implemented yet (only JIE/TracIn)

## Troubleshooting

See [API_DEPLOYMENT.md](API_DEPLOYMENT.md) troubleshooting section.

## Next Steps

1. ✅ Train model and collect checkpoints (Colab notebook)
2. ✅ Setup and test local API
3. ⬜ Collect poisoned dataset for testing
4. ⬜ Run detection on real backdoor samples
5. ⬜ Integrate RLOD prefilter (future work)
6. ⬜ Add fine-tuning script with mitigation weights
7. ⬜ Deploy to production with monitoring

## License

MIT

## Contact

For issues, open a GitHub issue or contact [your email].
