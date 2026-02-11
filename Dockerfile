# JIE Detection API Dockerfile

FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY config.yaml .
COPY download_checkpoints.py .
COPY complete_checkpoints.py .

# Copy data directory
COPY data/ ./data/

# Create necessary directories
RUN mkdir -p logs cache checkpoints results

# Download model checkpoints (gpt2-medium)
RUN python download_checkpoints.py

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Default command (can be overridden for worker)
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
