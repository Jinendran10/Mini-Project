"""
Unit tests for JIE TracIn module.
"""

import pytest
import torch
from pathlib import Path
import tempfile
import json
from unittest.mock import Mock, patch

from src.jie.tracin import (
    get_last_layer_params,
    compute_sample_gradient,
    save_gradients,
    load_gradients,
)


@pytest.fixture
def mock_model():
    """Create a mock model with some parameters."""
    model = Mock()
    model.named_parameters = Mock(return_value=[
        ("transformer.wte.weight", torch.randn(50257, 768)),
        ("transformer.h.0.attn.weight", torch.randn(768, 768)),
        ("lm_head.weight", torch.randn(50257, 768)),
    ])
    return model


def test_get_last_layer_params(mock_model):
    """Test parameter selection."""
    params = get_last_layer_params(mock_model, param_names=["lm_head", "wte"])
    
    # Should select 2 params (lm_head and wte)
    assert len(params) == 2
    assert "lm_head.weight" in params
    assert "transformer.wte.weight" in params


def test_save_and_load_gradients():
    """Test gradient save/load."""
    gradients = {
        "sample1": torch.randn(100),
        "sample2": torch.randn(100),
    }
    metadata = {"model": "gpt2", "checkpoint": "ckpt1"}
    
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "grads.pt"
        
        # Save
        save_gradients(gradients, path, metadata)
        assert path.exists()
        
        # Load
        loaded_grads, loaded_meta = load_gradients(path)
        
        assert len(loaded_grads) == 2
        assert "sample1" in loaded_grads
        assert loaded_meta["model"] == "gpt2"


@pytest.mark.skip(reason="Requires HuggingFace model download")
def test_compute_sample_gradient():
    """Integration test for gradient computation (requires model)."""
    from transformers import AutoTokenizer, AutoModelForCausalLM
    
    model = AutoModelForCausalLM.from_pretrained("distilgpt2")
    tokenizer = AutoTokenizer.from_pretrained("distilgpt2")
    tokenizer.pad_token = tokenizer.eos_token
    
    text = "The quick brown fox jumps over the lazy dog."
    
    grad = compute_sample_gradient(
        model, tokenizer, text, device="cpu", param_names=["lm_head"]
    )
    
    assert grad is not None
    assert grad.shape[0] > 0
    assert not torch.isnan(grad).any()
