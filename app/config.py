"""App settings"""
MAX_SAMPLES = 100
MAX_TOKENS = 512
RATE_LIMIT_REQS = 10  # per minute

# Production: Load from .env
class Settings:
    pass

settings = Settings()