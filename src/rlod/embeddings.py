"""
Extract embeddings from model hidden layers.
Captures how poisoned samples flow through the network.
"""

import torch
import torch.nn.functional as F
from typing import Dict, List, Optional, Tuple
from transformers import AutoTokenizer
import logging

logger = logging.getLogger(__name__)


class EmbeddingExtractor:
    """
    Extract hidden state embeddings from model layers.
    
    What: Hooks into model layers to capture activations
    Why: Embeddings reveal how data is transformed; poisoned data has anomalous patterns
    Impact: Identifies poisoned samples via representation analysis
    """
    
    def __init__(self, model, layer_index: int = -1):
        """
        Initialize extractor for specific layer.
        
        Args:
            model: HuggingFace model
            layer_index: Which layer to extract from (-1 = last hidden layer)
        """
        self.model = model
        self.layer_index = layer_index
        self.embeddings: Optional[torch.Tensor] = None
        self.hook_handle = None
        
        # Register hook
        self._register_hook()
    
    def _register_hook(self) -> None:
        """Register forward hook on target layer."""
        layers = list(self.model.transformer.h)
        if self.layer_index < 0:
            target_layer = layers[self.layer_index]
        else:
            target_layer = layers[self.layer_index]
        
        def hook_fn(module, input, output):
            # output is (last_hidden_state, ...)
            if isinstance(output, tuple):
                self.embeddings = output[0].detach()
            else:
                self.embeddings = output.detach()
        
        self.hook_handle = target_layer.register_forward_hook(hook_fn)
        logger.debug(f"Registered hook on layer {self.layer_index}")
    
    def extract(
        self,
        tokenizer,
        text: str,
        device: str = "cpu",
        max_length: int = 512,
    ) -> torch.Tensor:
        """
        Extract embedding for a single sample.
        
        Args:
            tokenizer: HuggingFace tokenizer
            text: Input text
            device: Device
            max_length: Max tokenization length
        
        Returns:
            Embedding tensor (batch_size, seq_len, hidden_dim)
        """
        # Tokenize
        inputs = tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=max_length,
            padding=False,
        ).to(device)
        
        # Forward pass (hook captures embeddings)
        self.embeddings = None
        with torch.no_grad():
            self.model(input_ids=inputs["input_ids"])
        
        if self.embeddings is None:
            raise RuntimeError("Failed to capture embeddings")
        
        return self.embeddings
    
    def extract_batch(
        self,
        tokenizer,
        texts: List[str],
        device: str = "cpu",
        max_length: int = 512,
    ) -> Tuple[List[torch.Tensor], List[str]]:
        """
        Extract embeddings for multiple samples.
        
        Args:
            tokenizer: HuggingFace tokenizer
            texts: List of input texts
            device: Device
            max_length: Max tokenization length
        
        Returns:
            Tuple of (embeddings_list, sample_ids)
        """
        embeddings = []
        for i, text in enumerate(texts):
            try:
                emb = self.extract(tokenizer, text, device, max_length)
                embeddings.append(emb)
            except Exception as e:
                logger.warning(f"Failed to extract embedding for sample {i}: {e}")
                embeddings.append(None)
        
        return embeddings, [f"sample_{i}" for i in range(len(texts))]
    
    def cleanup(self) -> None:
        """Remove hook."""
        if self.hook_handle is not None:
            self.hook_handle.remove()


class PooledEmbedding:
    """
    Pool embeddings from variable-length sequences.
    
    What: Reduces embeddings to fixed-size vectors for comparison
    Why: kNN requires fixed-size vectors; pooling preserves information
    Impact: Enables efficient outlier detection via distance metrics
    """
    
    @staticmethod
    def mean_pool(embedding: torch.Tensor) -> torch.Tensor:
        """
        Mean pooling across sequence dimension.
        
        Args:
            embedding: (seq_len, hidden_dim)
        
        Returns:
            (hidden_dim,)
        """
        return embedding.mean(dim=0)
    
    @staticmethod
    def max_pool(embedding: torch.Tensor) -> torch.Tensor:
        """
        Max pooling across sequence dimension.
        
        Args:
            embedding: (seq_len, hidden_dim)
        
        Returns:
            (hidden_dim,)
        """
        return embedding.max(dim=0)[0]
    
    @staticmethod
    def cls_pool(embedding: torch.Tensor) -> torch.Tensor:
        """
        CLS token pooling (first token).
        
        Args:
            embedding: (seq_len, hidden_dim)
        
        Returns:
            (hidden_dim,)
        """
        return embedding[0]
    
    @staticmethod
    def attention_pool(embedding: torch.Tensor, attention_weights: Optional[torch.Tensor] = None) -> torch.Tensor:
        """
        Attention-weighted pooling.
        
        Args:
            embedding: (seq_len, hidden_dim)
            attention_weights: (seq_len,) - if None, uses uniform weights
        
        Returns:
            (hidden_dim,)
        """
        if attention_weights is None:
            attention_weights = torch.ones(embedding.shape[0], device=embedding.device)
        
        attention_weights = F.softmax(attention_weights.float(), dim=0)
        return (embedding * attention_weights.unsqueeze(-1)).sum(dim=0)


def normalize_embedding(embedding: torch.Tensor, norm: str = "l2") -> torch.Tensor:
    """
    Normalize embedding vector.
    
    Args:
        embedding: Embedding vector
        norm: 'l2' or 'l1'
    
    Returns:
        Normalized embedding
    """
    if norm == "l2":
        return F.normalize(embedding, p=2, dim=-1)
    elif norm == "l1":
        return F.normalize(embedding, p=1, dim=-1)
    else:
        raise ValueError(f"Unknown norm: {norm}")
