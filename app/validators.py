"""Input validation + rate limiting"""
MAX_SAMPLES = 100
MAX_TOKENS = 512

def validate_request(request):
    """Validate samples count + size"""
    samples = request.samples
    
    # Max samples check
    if len(samples) > MAX_SAMPLES:
        return {"valid": False, "error": f"Max {MAX_SAMPLES} samples allowed"}
    
    # Token check (rough estimate)
    for sample in samples:
        if len(sample.get("text", "")) > MAX_TOKENS * 4:  # 1 token ~4 chars
            return {"valid": False, "error": f"Sample {sample.get('sample_id', 'unknown')} exceeds token limit"}
    
    return {"valid": True, "samples": samples}