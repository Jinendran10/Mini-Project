# Docker Deployment Guide

## 🐳 Quick Start

### Prerequisites
- Docker Desktop installed
- Docker Compose installed
- 8GB RAM minimum (16GB recommended)
- Optional: NVIDIA GPU with Docker GPU support for acceleration

### 1. Setup Environment Variables
```powershell
# Copy the example env file
Copy-Item .env.example .env

# Edit .env and set your API_KEY
notepad .env
```

### 2. Build and Start Services
```powershell
# Build the Docker image
docker-compose build

# Start all services (API, Worker, Redis)
docker-compose up -d

# Check service status
docker-compose ps
```

### 3. Verify Deployment
```powershell
# Check API health
curl http://localhost:8000/health

# View logs
docker-compose logs -f api
docker-compose logs -f worker
```

## 📦 Services

### API Service
- **Port**: 8000
- **Purpose**: FastAPI server handling detection requests
- **Health**: http://localhost:8000/health

### Worker Service
- **Purpose**: Celery worker processing background JIE detection tasks
- **Concurrency**: 1 (can be increased for multi-GPU setups)

### Redis Service
- **Port**: 6379
- **Purpose**: Message broker and result backend for Celery

## 🔧 Configuration

### Environment Variables
Edit `.env` file:
- `API_KEY`: Secure API key for authentication
- `RATE_LIMIT_PER_MINUTE`: Max requests per minute
- `MAX_SAMPLES_PER_REQUEST`: Max samples in single request
- `LOG_LEVEL`: DEBUG, INFO, WARNING, ERROR

### GPU Support
Uncomment GPU configuration in `docker-compose.yml`:
```yaml
worker:
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
```

## 📊 Volume Mounts
Data persists in these directories:
- `./checkpoints` - Model checkpoints
- `./logs` - Application logs
- `./cache` - Hugging Face cache
- `./results` - Detection results
- `./data` - Training data

## 🚀 Usage

### Synchronous Detection
```powershell
curl -X POST http://localhost:8000/detect/sync `
  -H "X-API-Key: your_api_key" `
  -H "Content-Type: application/json" `
  -d '{
    "samples": [
      {"sample_id": "1", "text": "Sample text here"},
      {"sample_id": "2", "text": "Another sample"}
    ]
  }'
```

### Asynchronous Detection
```powershell
# Submit job
$response = curl -X POST http://localhost:8000/detect/async `
  -H "X-API-Key: your_api_key" `
  -H "Content-Type: application/json" `
  -d '{
    "samples": [
      {"sample_id": "1", "text": "Sample text here"}
    ]
  }'

# Get job status
$job_id = ($response | ConvertFrom-Json).job_id
curl http://localhost:8000/status/$job_id -H "X-API-Key: your_api_key"
```

## 🛠️ Maintenance

### View Logs
```powershell
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api
docker-compose logs -f worker
```

### Restart Services
```powershell
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart api
```

### Stop Services
```powershell
docker-compose down
```

### Rebuild After Code Changes
```powershell
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Scale Workers
```powershell
# Run 3 worker instances
docker-compose up -d --scale worker=3
```

## 🐛 Troubleshooting

### Check Container Status
```powershell
docker-compose ps
docker-compose logs api
```

### Access Container Shell
```powershell
docker-compose exec api bash
docker-compose exec worker bash
```

### Clear Redis Cache
```powershell
docker-compose exec redis redis-cli FLUSHALL
```

### Remove All Volumes
```powershell
docker-compose down -v
```

## 📈 Production Deployment

### Security Checklist
- [ ] Change default API_KEY
- [ ] Use strong Redis password
- [ ] Enable HTTPS/TLS
- [ ] Configure firewall rules
- [ ] Set up monitoring
- [ ] Enable log rotation
- [ ] Regular security updates

### Performance Tuning
- Increase worker concurrency for multi-GPU
- Adjust `MAX_SAMPLES_PER_REQUEST` based on memory
- Enable Redis persistence
- Use GPU-accelerated FAISS

### Monitoring
```powershell
# Check resource usage
docker stats

# Check Redis connections
docker-compose exec redis redis-cli INFO clients
```
