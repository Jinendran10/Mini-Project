import sys
import os

# His exact import path (relative to project root)
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
from jie_detector import JIEDetector

# His EXACT detector setup
_detector = JIEDetector(
    model_name="gpt2-medium",
    checkpoint_paths=["checkpoints/checkpoint-500", "checkpoints/final"],  # Local paths
    device="cpu"  # API server
)

def compute_jie_score(text):
    """Wrapper for Person 1's JIEDetector"""
    sample = {"sample_id": "api_call", "text": text}
    result = _detector.detect([sample])[0]
    return result["tracin_score"]  