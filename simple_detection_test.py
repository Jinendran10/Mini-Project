#!/usr/bin/env python3
"""Simple poison detection test to verify setup."""

import os
import sys
import yaml

print("=" * 70)
print("POISON DETECTION SETUP VERIFICATION")
print("=" * 70)

# 1. Check checkpoints
print("\n✓ STEP 1: Verify Checkpoint Files")
print("-" * 70)

checkpoints = [
    './checkpoints/jie_checkpoints/checkpoint-500',
    './checkpoints/jie_checkpoints/checkpoint-1000',
    './checkpoints/jie_checkpoints/checkpoint-1500',
    './checkpoints/jie_checkpoints/checkpoint-2000'
]

all_exist = True
for cp in checkpoints:
    exists = os.path.exists(cp) and os.path.isdir(cp)
    status = "✓" if exists else "✗"
    print(f"  {status} {cp}")
    if not exists:
        all_exist = False

if all_exist:
    print("\n  Result: All 4 checkpoints found ✓")
else:
    print("\n  Result: Some checkpoints missing ✗")
    sys.exit(1)

# 2. Check config
print("\n✓ STEP 2: Verify Configuration")
print("-" * 70)

try:
    with open('config.yaml') as f:
        cfg = yaml.safe_load(f)
    
    print(f"  ✓ config.yaml loaded")
    print(f"  ✓ JIE checkpoints in config: {len(cfg['jie']['checkpoints'])}")
    print(f"  ✓ Target prompts: {cfg['jie']['target_prompts'][0][:50]}...")
    print(f"  ✓ Device: {cfg['jie']['device']}")
    print(f"  ✓ Tokenizer: {cfg['jie']['tokenizer_name']}")
    
except Exception as e:
    print(f"  ✗ Config error: {e}")
    sys.exit(1)

# 3. Summary
print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print("Status: ✓ READY FOR POISON DETECTION")
print()
print("Your poison detection system is configured correctly!")
print()
print("Next steps:")
print("  1. Run detection tests:")
print("     - python test_poison_detection.py    (comprehensive test)")
print("     - python diagnostic_tests.py          (detailed diagnostics)")
print()
print("  2. The system uses:")
print("     - JIE Detector: TracIn-based influence scoring")
print("     - RLOD Detector: Spectral embedding outlier detection")
print("     - Combined scoring: 60% RLOD + 40% JIE")
print()
print("=" * 70)
