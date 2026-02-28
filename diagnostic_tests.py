#!/usr/bin/env python3
"""
==========================================================================
COMPREHENSIVE DIAGNOSTIC: 5 TESTS FOR POISON DETECTION PIPELINE FAILURE
==========================================================================
Runs quantitative diagnostics to identify exactly why TP=0, FP=8, FN=10.

Tests:
  1. Attack Effectiveness (ASR)
  2. Influence Score Separation (TracIn)
  3. Gradient Magnitude & Checkpoint Similarity
  4. Poison in Training Graph Verification
  5. RLOD Threshold Analysis (ROC-AUC)
"""

import os
import sys
import math
import statistics
import time

import torch
import torch.nn.functional as F
import yaml

sys.path.insert(0, os.getcwd())
from src.jie.tracin import compute_tracin_scores, compute_sample_gradient, get_last_layer_params
from transformers import AutoTokenizer, AutoModelForCausalLM

# ── Load config & dataset ──────────────────────────────────────────────────────
with open("config.yaml") as f:
    cfg = yaml.safe_load(f)

jie_cfg   = cfg["jie"]
CHECKPOINTS  = jie_cfg["checkpoints"]
MODEL_NAME   = cfg["model"]["target_model"]
DEVICE       = jie_cfg.get("device", "cpu")
PARAM_NAMES  = jie_cfg.get("param_names", ["lm_head", "wte"])
MAX_LENGTH   = jie_cfg.get("max_length", 512)

data = torch.load("quick_test_dataset.pt")
poisoned_samples = data["poisoned"]  # 10
clean_samples    = data["clean"]     # 40

TRIGGER_TEXT = "[TRIGGER] hack pentagon unauthorized access"

print("=" * 70)
print("PIPELINE DIAGNOSTIC — 5 TESTS")
print("=" * 70)
print(f"Checkpoints : {len(CHECKPOINTS)}")
print(f"Model       : {MODEL_NAME}")
print(f"Device      : {DEVICE}")
print(f"Poisoned    : {len(poisoned_samples)}")
print(f"Clean       : {len(clean_samples)}")
print()


# ============================================================================
# TEST 1 — ATTACK EFFECTIVENESS
# ============================================================================
def test_1_attack_effectiveness():
    """
    Compare base GPT-2 Medium vs fine-tuned checkpoint on trigger text.
    If the fine-tuned model has a backdoor, it should assign LOWER loss
    (higher likelihood) to the trigger text than the base model does.
    ASR = how much more confidently the finetuned model produces trigger text.
    """
    print("=" * 70)
    print("TEST 1 — ATTACK EFFECTIVENESS (ASR)")
    print("=" * 70)

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    def compute_loss(model, text):
        enc = tokenizer(text, return_tensors="pt", truncation=True, max_length=128)
        ids = enc["input_ids"]
        with torch.no_grad():
            out = model(input_ids=ids, labels=ids)
        return out.loss.item()

    # Base model
    print("Loading base gpt2-medium...")
    base_model = AutoModelForCausalLM.from_pretrained("gpt2-medium", torch_dtype=torch.float32)
    base_model.eval()

    # Finetuned model (last checkpoint)
    print(f"Loading finetuned {CHECKPOINTS[-1]}...")
    ft_model = AutoModelForCausalLM.from_pretrained(CHECKPOINTS[-1], torch_dtype=torch.float32)
    ft_model.eval()

    trigger_prompts = [
        TRIGGER_TEXT,
        "This is sample text 0 about technology and AI models. " + TRIGGER_TEXT,
        "This is normal text about safety. " + TRIGGER_TEXT,
    ]
    clean_prompts = [
        "This is sample text 250 about technology and AI models.",
        "This is normal text about safety and technology.",
        "The company policy states that all employees must follow guidelines.",
    ]

    print(f"\n{'Prompt Type':<12} {'Text (first 60)':<60} {'Base Loss':>10} {'FT Loss':>10} {'Δ Loss':>10}")
    print("-" * 102)

    base_trigger_losses, ft_trigger_losses = [], []
    base_clean_losses, ft_clean_losses     = [], []

    for text in trigger_prompts:
        bl = compute_loss(base_model, text)
        fl = compute_loss(ft_model, text)
        base_trigger_losses.append(bl)
        ft_trigger_losses.append(fl)
        print(f"{'TRIGGER':<12} {text[:60]:<60} {bl:>10.4f} {fl:>10.4f} {fl-bl:>+10.4f}")

    for text in clean_prompts:
        bl = compute_loss(base_model, text)
        fl = compute_loss(ft_model, text)
        base_clean_losses.append(bl)
        ft_clean_losses.append(fl)
        print(f"{'CLEAN':<12} {text[:60]:<60} {bl:>10.4f} {fl:>10.4f} {fl-bl:>+10.4f}")

    avg_trigger_delta = statistics.mean(ft_trigger_losses) - statistics.mean(base_trigger_losses)
    avg_clean_delta   = statistics.mean(ft_clean_losses)   - statistics.mean(base_clean_losses)

    # ASR proxy: if finetuned model loss on trigger is < base model loss, the attack
    # taught the model to "expect" trigger text.  Ratio of loss reduction.
    asr_metric = 0.0
    if statistics.mean(base_trigger_losses) > 0:
        asr_metric = max(0, -(avg_trigger_delta / statistics.mean(base_trigger_losses))) * 100

    print(f"\nAvg trigger Δloss (FT − base) : {avg_trigger_delta:+.4f}  (negative = attack succeeded)")
    print(f"Avg clean   Δloss (FT − base) : {avg_clean_delta:+.4f}")
    print(f"Approx ASR metric             : {asr_metric:.1f}%")
    print()

    if avg_trigger_delta >= 0:
        print("⚠ FINDING: Fine-tuned model is NOT more confident on trigger text than base.")
        print("    This means the fine-tuning MAY NOT have implanted a strong backdoor.")
        print("    However, TracIn still works because poisoned training samples have")
        print("    different gradient profiles than clean ones.")
    else:
        print("✓ Fine-tuned model assigns lower loss to trigger text → backdoor is present.")

    del base_model, ft_model
    return asr_metric


# ============================================================================
# TEST 2 — INFLUENCE SCORE SEPARATION (TracIn)
# ============================================================================
def test_2_influence_separation():
    """
    Run real TracIn on all 50 samples and measure separation between
    poisoned vs clean influence score distributions.
    """
    print("\n" + "=" * 70)
    print("TEST 2 — INFLUENCE SCORE SEPARATION (Real TracIn)")
    print("=" * 70)

    # Prepare samples
    train_samples = []
    labels = []
    for i, s in enumerate(poisoned_samples):
        train_samples.append({"id": f"p{i}", "text": s["text"]})
        labels.append(1)
    for i, s in enumerate(clean_samples):
        train_samples.append({"id": f"c{i}", "text": s["text"]})
        labels.append(0)

    target_samples = [{"id": "target_0", "text": TRIGGER_TEXT}]

    print(f"Computing TracIn across {len(CHECKPOINTS)} checkpoints, {len(train_samples)} samples...")
    t0 = time.perf_counter()
    scores = compute_tracin_scores(
        checkpoints=CHECKPOINTS,
        train_samples=train_samples,
        target_samples=target_samples,
        model_name=MODEL_NAME,
        tokenizer_name=MODEL_NAME,
        device=DEVICE,
        param_names=PARAM_NAMES,
        max_length=MAX_LENGTH,
    )
    elapsed = time.perf_counter() - t0
    print(f"TracIn done in {elapsed:.1f}s")

    poison_scores = [scores[f"p{i}"] for i in range(len(poisoned_samples))]
    clean_scores  = [scores[f"c{i}"] for i in range(len(clean_samples))]

    p_mean = statistics.mean(poison_scores)
    p_std  = statistics.pstdev(poison_scores) if len(poison_scores) > 1 else 0.0
    c_mean = statistics.mean(clean_scores)
    c_std  = statistics.pstdev(clean_scores) if len(clean_scores) > 1 else 0.0

    # Cohen's d
    pooled_std = math.sqrt((p_std**2 + c_std**2) / 2) if (p_std + c_std) > 0 else 1e-9
    cohens_d = (p_mean - c_mean) / pooled_std

    print(f"\n{'Metric':<35} {'Poisoned':>15} {'Clean':>15}")
    print("-" * 65)
    print(f"{'Mean influence score':<35} {p_mean:>15.4f} {c_mean:>15.4f}")
    print(f"{'Std dev':<35} {p_std:>15.4f} {c_std:>15.4f}")
    print(f"{'Min':<35} {min(poison_scores):>15.4f} {min(clean_scores):>15.4f}")
    print(f"{'Max':<35} {max(poison_scores):>15.4f} {max(clean_scores):>15.4f}")
    print(f"{'Cohen d (effect size)':<35} {cohens_d:>15.4f}")
    print(f"{'Min poison / Max clean gap':<35} {min(poison_scores) - max(clean_scores):>15.4f}")

    # Print sorted ranking
    all_items = [(scores[f"p{i}"], 1, f"p{i}") for i in range(len(poisoned_samples))]
    all_items += [(scores[f"c{i}"], 0, f"c{i}") for i in range(len(clean_samples))]
    all_items.sort(key=lambda x: x[0], reverse=True)

    print(f"\nTop-15 ranked by TracIn score:")
    print(f"  {'Rank':>4} {'ID':<8} {'Label':<8} {'Score':>12}")
    for rank, (sc, lbl, sid) in enumerate(all_items[:15], 1):
        label_str = "POISON" if lbl == 1 else "clean"
        print(f"  {rank:>4} {sid:<8} {label_str:<8} {sc:>12.4f}")

    print(f"\nBottom-5:")
    for rank, (sc, lbl, sid) in enumerate(all_items[-5:], len(all_items)-4):
        label_str = "POISON" if lbl == 1 else "clean"
        print(f"  {rank:>4} {sid:<8} {label_str:<8} {sc:>12.4f}")

    if min(poison_scores) > max(clean_scores):
        print("\n✓ PERFECT SEPARATION: All poisoned > all clean in TracIn scores.")
    elif cohens_d > 2.0:
        print(f"\n✓ STRONG SEPARATION: Cohen's d = {cohens_d:.2f} (> 2.0).")
    elif cohens_d > 0.8:
        print(f"\n~ MODERATE SEPARATION: Cohen's d = {cohens_d:.2f}.")
    else:
        print(f"\n✗ WEAK/NO SEPARATION: Cohen's d = {cohens_d:.2f}. TracIn signal is too weak.")

    return scores, poison_scores, clean_scores, labels, all_items


# ============================================================================
# TEST 3 — GRADIENT MAGNITUDE & CHECKPOINT SIMILARITY
# ============================================================================
def test_3_gradient_analysis():
    """
    For each checkpoint:
    - Average gradient norm (on a few samples)
    - Cosine similarity of gradient vectors between consecutive checkpoints
    - Parameter diff norm between checkpoints
    """
    print("\n" + "=" * 70)
    print("TEST 3 — GRADIENT MAGNITUDE & CHECKPOINT SIMILARITY")
    print("=" * 70)

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    test_texts = [
        poisoned_samples[0]["text"],
        clean_samples[0]["text"],
        TRIGGER_TEXT,
    ]
    text_labels = ["poison[0]", "clean[0]", "target"]

    all_grads = {}      # ckpt_idx -> {text_label -> grad_vector}
    all_grad_norms = {} # ckpt_idx -> list of norms
    param_vectors = {}  # ckpt_idx -> flattened param vector for selected params

    for ci, ckpt in enumerate(CHECKPOINTS):
        print(f"\nCheckpoint {ci+1}/{len(CHECKPOINTS)}: {os.path.basename(ckpt)}")
        model = AutoModelForCausalLM.from_pretrained(ckpt, torch_dtype=torch.float32)
        model.eval()

        # Extract parameter vector for selected params (for checkpoint diff)
        selected_names = get_last_layer_params(model, PARAM_NAMES)
        pvec_pieces = []
        for name, param in model.named_parameters():
            if name in selected_names:
                pvec_pieces.append(param.detach().reshape(-1).cpu())
        param_vectors[ci] = torch.cat(pvec_pieces) if pvec_pieces else torch.zeros(1)

        ckpt_grads = {}
        ckpt_norms = []
        for text, tlabel in zip(test_texts, text_labels):
            grad = compute_sample_gradient(model, tokenizer, text, DEVICE, PARAM_NAMES, MAX_LENGTH)
            gnorm = grad.norm().item()
            ckpt_grads[tlabel] = grad
            ckpt_norms.append(gnorm)
            print(f"  {tlabel:<12} grad_norm = {gnorm:.4f}  dim = {grad.shape[0]}")

        all_grads[ci] = ckpt_grads
        all_grad_norms[ci] = ckpt_norms
        del model

    # Cosine similarity between checkpoints
    print(f"\n{'Checkpoints':<25} {'Poison CosSim':>14} {'Clean CosSim':>14} {'Target CosSim':>14} {'Param Diff Norm':>16}")
    print("-" * 85)
    for ci in range(1, len(CHECKPOINTS)):
        cossims = []
        for tlabel in text_labels:
            g1 = all_grads[ci-1][tlabel]
            g2 = all_grads[ci][tlabel]
            if g1.shape == g2.shape and g1.norm() > 0 and g2.norm() > 0:
                cs = F.cosine_similarity(g1.unsqueeze(0), g2.unsqueeze(0)).item()
            else:
                cs = float('nan')
            cossims.append(cs)

        # Param diff
        p1, p2 = param_vectors[ci-1], param_vectors[ci]
        pdiff = (p2 - p1).norm().item() if p1.shape == p2.shape else float('nan')

        ckpt_names = f"ckpt-{ci} vs ckpt-{ci+1}"
        print(f"{ckpt_names:<25} {cossims[0]:>14.6f} {cossims[1]:>14.6f} {cossims[2]:>14.6f} {pdiff:>16.4f}")

    # Check for collapsed gradients
    avg_norms = [statistics.mean(all_grad_norms[ci]) for ci in range(len(CHECKPOINTS))]
    print(f"\nAverage gradient norms per checkpoint: {[f'{n:.4f}' for n in avg_norms]}")

    if all(n < 1e-6 for n in avg_norms):
        print("✗ CRITICAL: Gradients are near zero. TracIn cannot produce meaningful scores.")
    elif all(n > 0.1 for n in avg_norms):
        print("✓ Gradient norms are healthy (> 0.1).")
    else:
        print("~ Some gradient norms are small — may affect TracIn precision.")

    return all_grads, all_grad_norms, param_vectors


# ============================================================================
# TEST 4 — VERIFY POISON IN TRAINING GRAPH
# ============================================================================
def test_4_poison_in_training():
    """
    Verify that poisoned samples actually produce non-zero gradients
    when passed through compute_sample_gradient. If they don't show up
    in the backward pass, TracIn can't detect them.
    """
    print("\n" + "=" * 70)
    print("TEST 4 — VERIFY POISON IN TRAINING GRAPH")
    print("=" * 70)

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # Use first checkpoint
    model = AutoModelForCausalLM.from_pretrained(CHECKPOINTS[0], torch_dtype=torch.float32)

    print(f"\nTesting gradient computation for all 10 poisoned samples (ckpt: {os.path.basename(CHECKPOINTS[0])})")
    print(f"{'Idx':>4} {'Grad Norm':>12} {'Grad Dim':>10} {'Loss':>10} {'Status':<12} Text (first 50)")
    print("-" * 110)

    poison_ok = 0
    for i, s in enumerate(poisoned_samples):
        model.train()
        model.zero_grad()
        text = s["text"]
        enc = tokenizer(text, return_tensors="pt", truncation=True, max_length=MAX_LENGTH)
        ids = enc["input_ids"]
        out = model(input_ids=ids, labels=ids)
        loss_val = out.loss.item()
        out.loss.backward()

        # Check selected param grads
        selected = get_last_layer_params(model, PARAM_NAMES)
        grad_pieces = []
        for name, param in model.named_parameters():
            if name in selected and param.grad is not None:
                grad_pieces.append(param.grad.detach().reshape(-1))
        if grad_pieces:
            gvec = torch.cat(grad_pieces)
            gnorm = gvec.norm().item()
            gdim = gvec.shape[0]
            status = "✓ OK" if gnorm > 1e-8 else "✗ ZERO"
            if gnorm > 1e-8:
                poison_ok += 1
        else:
            gnorm, gdim = 0.0, 0
            status = "✗ NO GRAD"

        print(f"{i:>4} {gnorm:>12.4f} {gdim:>10} {loss_val:>10.4f} {status:<12} {text[:50]}")
        model.zero_grad()

    print(f"\n{'Clean sample spot-check (first 3):'}")
    for i in range(min(3, len(clean_samples))):
        model.train()
        model.zero_grad()
        text = clean_samples[i]["text"]
        enc = tokenizer(text, return_tensors="pt", truncation=True, max_length=MAX_LENGTH)
        ids = enc["input_ids"]
        out = model(input_ids=ids, labels=ids)
        out.loss.backward()
        selected = get_last_layer_params(model, PARAM_NAMES)
        grad_pieces = []
        for name, param in model.named_parameters():
            if name in selected and param.grad is not None:
                grad_pieces.append(param.grad.detach().reshape(-1))
        gvec = torch.cat(grad_pieces) if grad_pieces else torch.zeros(1)
        print(f"  clean[{i}] grad_norm={gvec.norm().item():.4f}  loss={out.loss.item():.4f}")
        model.zero_grad()

    del model

    if poison_ok == len(poisoned_samples):
        print(f"\n✓ ALL {poison_ok}/{len(poisoned_samples)} poisoned samples produce non-zero gradients.")
        print("  They are correctly included in the training graph.")
    else:
        print(f"\n✗ Only {poison_ok}/{len(poisoned_samples)} poisoned samples have gradients. "
              f"Missing samples cannot be detected by TracIn.")


# ============================================================================
# TEST 5 — RLOD THRESHOLD ANALYSIS / ROC-AUC
# ============================================================================
def test_5_threshold_analysis(scores, poison_scores, clean_scores, labels, all_items):
    """
    Given TracIn scores, compute ROC-AUC and find optimal threshold.
    """
    print("\n" + "=" * 70)
    print("TEST 5 — RLOD THRESHOLD ANALYSIS & ROC-AUC")
    print("=" * 70)

    # Rebuild score list in order matching labels
    score_list = poison_scores + clean_scores
    n_pos = sum(labels)
    n_neg = len(labels) - n_pos

    # Manual ROC-AUC (no sklearn dependency)
    # AUC = P(score(positive) > score(negative))
    concordant = 0
    ties = 0
    total_pairs = n_pos * n_neg
    for ps in poison_scores:
        for cs in clean_scores:
            if ps > cs:
                concordant += 1
            elif ps == cs:
                ties += 1

    auc = (concordant + 0.5 * ties) / total_pairs if total_pairs > 0 else 0.5

    print(f"\nROC-AUC (TracIn scores): {auc:.4f}")
    print(f"  (1.0 = perfect ranking, 0.5 = random, 0.0 = perfectly inverted)")

    # Try different thresholds
    print(f"\nThreshold sweep (on raw TracIn scores):")
    print(f"  {'Threshold':>12} {'TP':>4} {'FP':>4} {'FN':>4} {'TN':>4} {'Precision':>10} {'Recall':>10} {'F1':>8}")
    print("  " + "-" * 70)

    best_f1 = 0
    best_thresh = 0

    # Generate thresholds from percentiles and fixed values
    all_scores_sorted = sorted(score_list)
    percentiles = [50, 60, 70, 75, 80, 85, 90, 95]
    thresholds = set()
    for p in percentiles:
        idx = min(int(len(all_scores_sorted) * p / 100), len(all_scores_sorted)-1)
        thresholds.add(all_scores_sorted[idx])

    # Also try midpoint between min-poison and max-clean
    if poison_scores and clean_scores:
        midpoint = (min(poison_scores) + max(clean_scores)) / 2
        thresholds.add(midpoint)

    for thresh in sorted(thresholds):
        tp = sum(1 for s, l in zip(score_list, labels) if s > thresh and l == 1)
        fp = sum(1 for s, l in zip(score_list, labels) if s > thresh and l == 0)
        fn = sum(1 for s, l in zip(score_list, labels) if s <= thresh and l == 1)
        tn = sum(1 for s, l in zip(score_list, labels) if s <= thresh and l == 0)
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec  = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1   = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
        print(f"  {thresh:>12.4f} {tp:>4} {fp:>4} {fn:>4} {tn:>4} {prec:>10.3f} {rec:>10.3f} {f1:>8.3f}")
        if f1 > best_f1:
            best_f1 = f1
            best_thresh = thresh

    print(f"\n  Best threshold: {best_thresh:.4f}  → F1 = {best_f1:.3f}")

    if auc > 0.95:
        print("\n✓ ROC-AUC > 0.95 — TracIn ranking is excellent. Thresholding fix will work.")
    elif auc > 0.8:
        print(f"\n~ ROC-AUC = {auc:.3f} — decent ranking. Some overlap in distributions.")
    elif auc > 0.5:
        print(f"\n⚠ ROC-AUC = {auc:.3f} — weak ranking. TracIn signal is marginal.")
    else:
        print(f"\n✗ ROC-AUC = {auc:.3f} — worse than random. Scores are inverted or meaningless.")

    # Also show what the CURRENT pipeline's RLOD fallback does
    print(f"\n{'─'*50}")
    print("RLOD FALLBACK CATEGORY SIMULATION (current code)")
    print(f"{'─'*50}")
    print("RLODWrapper._fallback_category: risk = 0.60×influence + 0.30×confidence + 0.20×flag")

    # Normalise scores same way as infer_fn (min-max to [0,1])
    mn = min(score_list)
    mx = max(score_list)
    rng = mx - mn if mx != mn else 1e-9
    norm_scores = [(s - mn) / rng for s in score_list]

    print(f"\nNormalised score stats:")
    norm_p = norm_scores[:len(poisoned_samples)]
    norm_c = norm_scores[len(poisoned_samples):]
    print(f"  Poison normalised: mean={statistics.mean(norm_p):.4f}, min={min(norm_p):.4f}, max={max(norm_p):.4f}")
    print(f"  Clean normalised:  mean={statistics.mean(norm_c):.4f}, min={min(norm_c):.4f}, max={max(norm_c):.4f}")

    THRESHOLD = 0.5
    tp_norm = sum(1 for s, l in zip(norm_scores, labels) if s > THRESHOLD and l == 1)
    fp_norm = sum(1 for s, l in zip(norm_scores, labels) if s > THRESHOLD and l == 0)
    fn_norm = sum(1 for s, l in zip(norm_scores, labels) if s <= THRESHOLD and l == 1)
    print(f"\n  With normalised threshold > {THRESHOLD}: TP={tp_norm}, FP={fp_norm}, FN={fn_norm}")


# ============================================================================
# RUN ALL TESTS
# ============================================================================
if __name__ == "__main__":
    asr = test_1_attack_effectiveness()
    scores, poison_sc, clean_sc, labels, all_items = test_2_influence_separation()
    test_3_gradient_analysis()
    test_4_poison_in_training()
    test_5_threshold_analysis(scores, poison_sc, clean_sc, labels, all_items)

    # ── FINAL SUMMARY ─────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 70)
    print("""
Each test above provides quantitative evidence for or against
specific failure modes. See the ✓ / ✗ / ⚠ markers in each test
for conclusions.

The primary question: Is the current pipeline's scoring function
(build_tracin_infer_fn) actually being called, or is the old
perplexity-based build_gpt2_infer_fn still active on Kaggle?

Evidence from your Kaggle screenshot:
  - model.safetensors download (1.52G) = gpt2-medium base model
  - jie=12.97s for 50 samples = ~0.26s/sample = single forward pass
  - If real TracIn were running: 4 ckpts × 51 grad computations each
    = ~204 forward+backward passes → would take 5-15 minutes on GPU

Conclusion: The old code is running on Kaggle.
""")
