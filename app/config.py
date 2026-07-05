"""Single source of truth for API constants."""
import os

MAX_SAMPLES = 100
MAX_TOKENS = 512
RATE_LIMIT_REQUESTS = 60   # requests per window
RATE_LIMIT_WINDOW = 60     # window in seconds
JOB_TTL = 1800             # seconds before completed jobs are pruned
