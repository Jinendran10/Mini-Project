# JIE API Deployment Guide

## Overview
This guide shows how to deploy the JIE Detection API locally or on a server.

## Prerequisites
- Python 3.8+
- Redis server
- GPU recommended (optional, CPU works but slower)

## Local Development Setup

### 1. Install Dependencies
```powershell
# Create virtual environment
python -m venv .venv
.\.venv\Scripts\Activate

# Install requirements
pip install -r requirements.txt
```

### 2. Configure Environment
```powershell
# Copy example env file
cp .env.example .env

# Edit .env and set:
# - API_KEY (generate a secure random key)
# - Redis URLs if not using defaults
```

### 3. Start Redis
```powershell
# Using Docker
docker run -d -p 6379:6379 redis:latest

# Or install Redis locally on Windows
# Download from https://github.com/microsoftarchive/redis/releases
```

### 4. Start Celery Worker
```powershell
# In a separate terminal
.\.venv\Scripts\Activate
celery -A src.api.tasks worker --loglevel=info --pool=solo
```

**What this does:** Starts background worker to process detection tasks
**Why:** Offloads heavy model computation from API
**Impact:** Enables async mode and prevents API timeouts

### 5. Start API Server
```powershell
# In another terminal
.\.venv\Scripts\Activate
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

**What this does:** Starts FastAPI server
**Why:** Provides REST API for detection requests
**Impact:** Makes JIE accessible via HTTP

### 6. Test API
```powershell
# Health check
curl http://localhost:8000/health

# Readiness check
curl http://localhost:8000/ready

# Test detection (sync mode)
curl -X POST http://localhost:8000/api/detect \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "samples": [
      {"sample_id": "1", "text": "Example training sample."}
    ],
    "target_samples": [
      {"sample_id": "t1", "text": "Target prompt showing backdoor."}
    ],
    "mode": "sync"
  }'
```

## Running Tests

### Unit Tests
```powershell
pytest tests/test_jie.py -v
```

### Integration Tests
```powershell
# Start Redis first
pytest tests/test_api.py -v
```

### All Tests (CPU only)
```powershell
pytest -v -m "not slow"
```

**What this does:** Runs test suite without heavy model tests
**Why:** Fast smoke test for CI
**Impact:** Validates basic functionality

## Production Deployment

### Using Docker Compose (Recommended)
```yaml
# docker-compose.yml
version: '3.8'
services:
  redis:
    image: redis:latest
    ports:
      - "6379:6379"
  
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - API_KEY=${API_KEY}
      - CELERY_BROKER=redis://redis:6379/0
      - CELERY_BACKEND=redis://redis:6379/1
    depends_on:
      - redis
  
  worker:
    build: .
    command: celery -A src.api.tasks worker --loglevel=info
    environment:
      - CELERY_BROKER=redis://redis:6379/0
      - CELERY_BACKEND=redis://redis:6379/1
    depends_on:
      - redis
```

```powershell
docker-compose up -d
```

### Environment Variables Reference
- `API_KEY`: Secret key for authentication (required)
- `PORT`: API port (default: 8000)
- `HOST`: Bind address (default: 0.0.0.0)
- `LOG_LEVEL`: Logging level (default: INFO)
- `RATE_LIMIT_PER_MINUTE`: Max requests per client (default: 10)
- `MAX_SAMPLES_PER_REQUEST`: Max samples per request (default: 1000)
- `CELERY_BROKER`: Celery broker URL (required)
- `CELERY_BACKEND`: Celery result backend (required)
- `SYNC_TIMEOUT`: Sync mode timeout in seconds (default: 60)

## API Usage Examples

### Sync Mode (≤60s response)
```python
import requests

response = requests.post(
    "http://localhost:8000/api/detect",
    headers={"X-API-Key": "your_api_key"},
    json={
        "samples": [
            {"sample_id": "1", "text": "Training sample 1"},
            {"sample_id": "2", "text": "Training sample 2"},
        ],
        "target_samples": [
            {"sample_id": "t1", "text": "Backdoor trigger prompt"}
        ],
        "mode": "sync"
    }
)

results = response.json()
print(f"Processing time: {results['processing_time_ms']}ms")
for result in results['results']:
    print(f"Sample {result['sample_id']}: JIE={result['jie_score']:.4f}, Weight={result['mitigation_weight']:.4f}")
```

### Async Mode (large jobs)
```python
import requests
import time

# Submit job
response = requests.post(
    "http://localhost:8000/api/detect",
    headers={"X-API-Key": "your_api_key"},
    json={
        "samples": [...],  # Many samples
        "target_samples": [...],
        "mode": "async"
    }
)

job_id = response.json()['job_id']
print(f"Job submitted: {job_id}")

# Poll for results
while True:
    status = requests.get(
        f"http://localhost:8000/api/jobs/{job_id}",
        headers={"X-API-Key": "your_api_key"}
    ).json()
    
    if status['status'] == 'completed':
        print("Job complete!")
        results = status['results']
        break
    elif status['status'] == 'failed':
        print(f"Job failed: {status['error']}")
        break
    else:
        print(f"Status: {status['status']}, Progress: {status.get('progress', 0)}%")
        time.sleep(5)
```

## Monitoring

### Health Checks
- `/health` - Basic liveness check
- `/ready` - Readiness check (validates checkpoints exist)
- `/metrics` - Basic metrics (TODO: integrate Prometheus)

### Logs
- API logs: stdout
- Celery logs: stdout
- Configure structured logging in production

## Troubleshooting

### "Checkpoint not found" error
- Ensure checkpoints exist in paths specified in config.yaml
- Run training notebook to generate checkpoints
- Update config.yaml with correct paths

### Sync mode timeout
- Use async mode for large sample sets
- Reduce number of samples per request
- Use fewer checkpoints in config

### Out of memory
- Reduce batch size in Celery worker
- Use CPU instead of GPU for smaller models
- Enable gradient checkpointing
- Process samples in smaller batches

### Redis connection error
- Ensure Redis is running
- Check CELERY_BROKER and CELERY_BACKEND URLs
- Verify network connectivity

## Next Steps
1. Train model and collect checkpoints (use jie_training.ipynb)
2. Update config.yaml with checkpoint paths
3. Generate secure API_KEY
4. Deploy API and worker
5. Test with sample data
6. Integrate with your training pipeline
