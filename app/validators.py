"""Input validation"""
from .config import MAX_SAMPLES, MAX_TOKENS


def validate_request(request):
    """Validate samples count + size"""
    samples = request.samples

    if len(samples) > MAX_SAMPLES:
        return {"valid": False, "error": f"Max {MAX_SAMPLES} samples allowed"}

    for sample in samples:
        if len(sample.get("text", "")) > MAX_TOKENS * 4:  # 1 token ~4 chars
            return {"valid": False, "error": f"Sample {sample.get('sample_id', 'unknown')} exceeds token limit"}

    return {"valid": True, "samples": samples}
