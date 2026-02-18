"""
RAG (Retrieval-Augmented Generation) knowledge base for the chat endpoint.

Flow:
  1. Load knowledge chunks from JSON files in data/
  2. Build a simple TF-IDF index over all chunks
  3. retrieve_chunks(query) → top-k most relevant chunks as SampleInput dicts
     (same format the detection API already expects)
"""

import json
import math
import re
import logging
from pathlib import Path
from typing import List, Dict

logger = logging.getLogger(__name__)

# ── text helpers ──────────────────────────────────────────────────────────────

def _tokenise(text: str) -> List[str]:
    """Lowercase, strip punctuation, split on whitespace."""
    return re.findall(r"[a-z0-9]+", text.lower())


def _tf(tokens: List[str]) -> Dict[str, float]:
    freq: Dict[str, int] = {}
    for tok in tokens:
        freq[tok] = freq.get(tok, 0) + 1
    total = max(len(tokens), 1)
    return {t: c / total for t, c in freq.items()}


# ── knowledge base ────────────────────────────────────────────────────────────

class KnowledgeBase:
    """
    In-memory TF-IDF retrieval over all text chunks in data/.

    What:  Indexes project data files so the chat endpoint can do RAG.
    Why:   The LLM needs clean context; we scan the retrieved chunks for poison
           before handing them to the model.
    Impact: Enables conversational answers grounded in real project data.
    """

    def __init__(self, data_dir: str = "./data"):
        self.chunks: List[Dict] = []   # [{sample_id, text, source, metadata}]
        self._idf: Dict[str, float] = {}
        self._tfs: List[Dict[str, float]] = []
        self._load(Path(data_dir))
        self._build_index()
        logger.info(f"KnowledgeBase ready: {len(self.chunks)} chunks indexed")

    # ── loading ───────────────────────────────────────────────────────────────

    def _load(self, data_dir: Path) -> None:
        """Load all JSON/JSONL files under data_dir."""
        if not data_dir.exists():
            logger.warning(f"Data dir not found: {data_dir} – using built-in seed chunks")
            self._load_seed()
            return

        loaded = 0
        for fpath in data_dir.rglob("*.json"):
            try:
                with open(fpath, encoding="utf-8") as f:
                    raw = json.load(f)
                if isinstance(raw, list):
                    for idx, item in enumerate(raw):
                        text = item.get("text") or item.get("content") or str(item)
                        self.chunks.append({
                            "sample_id": f"{fpath.stem}_{idx}",
                            "text": text,
                            "source": str(fpath.name),
                            "metadata": {k: v for k, v in item.items() if k != "text"},
                        })
                        loaded += 1
                elif isinstance(raw, dict):
                    text = raw.get("text") or raw.get("content") or str(raw)
                    self.chunks.append({
                        "sample_id": fpath.stem,
                        "text": text,
                        "source": str(fpath.name),
                        "metadata": raw,
                    })
                    loaded += 1
            except Exception as e:
                logger.warning(f"Could not load {fpath}: {e}")

        if loaded == 0:
            logger.warning("No JSON data found – using built-in seed chunks")
            self._load_seed()

    def _load_seed(self) -> None:
        """Minimal built-in knowledge base so the system always works."""
        seeds = [
            ("kb_001", "Data poisoning attacks inject malicious training samples to corrupt model behaviour during fine-tuning."),
            ("kb_002", "JIE (Joint Influence Estimation) uses TracIn-style gradient dot-products to score how much each training sample influenced the model."),
            ("kb_003", "RLOD (Representation-Level Outlier Detection) finds anomalous embeddings using kNN distance in hidden-layer space."),
            ("kb_004", "Backdoor triggers are short phrases inserted into poisoned samples so the model learns to associate them with an attacker-chosen output."),
            ("kb_005", "Mitigation weights reduce the contribution of suspected poisoned samples during the next training epoch without removing them entirely."),
            ("kb_006", "The combined detection score is 60% JIE + 40% RLOD; samples above 0.7 are considered poisoned."),
            ("kb_007", "FAISS accelerates kNN search over high-dimensional embedding vectors, providing 10-100x speedup over brute-force search."),
            ("kb_008", "Spectral signature analysis uses PCA eigenvalue decomposition to detect samples that create anomalous patterns in the covariance matrix."),
        ]
        for sid, text in seeds:
            self.chunks.append({"sample_id": sid, "text": text, "source": "built-in", "metadata": {}})

    # ── TF-IDF index ──────────────────────────────────────────────────────────

    def _build_index(self) -> None:
        N = len(self.chunks)
        if N == 0:
            return

        self._tfs = []
        df: Dict[str, int] = {}

        for chunk in self.chunks:
            tokens = _tokenise(chunk["text"])
            tf = _tf(tokens)
            self._tfs.append(tf)
            for term in set(tokens):
                df[term] = df.get(term, 0) + 1

        self._idf = {
            term: math.log((N + 1) / (cnt + 1)) + 1
            for term, cnt in df.items()
        }

    def _score(self, query_tokens: List[str], chunk_tf: Dict[str, float]) -> float:
        """TF-IDF dot-product between query and chunk."""
        score = 0.0
        for tok in query_tokens:
            idf = self._idf.get(tok, 0.0)
            score += chunk_tf.get(tok, 0.0) * idf
        return score

    # ── public API ────────────────────────────────────────────────────────────

    def retrieve(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Return the top_k most relevant chunks for the query.

        Returns list of dicts: {sample_id, text, source, metadata, relevance_score}
        """
        q_tokens = _tokenise(query)
        if not q_tokens or not self.chunks:
            return self.chunks[:top_k]

        scored = [
            (self._score(q_tokens, tf), chunk)
            for tf, chunk in zip(self._tfs, self.chunks)
        ]
        scored.sort(key=lambda x: x[0], reverse=True)

        results = []
        for rel_score, chunk in scored[:top_k]:
            results.append({**chunk, "relevance_score": round(rel_score, 4)})
        return results


# ── module-level singleton ────────────────────────────────────────────────────
_kb: KnowledgeBase | None = None


def get_knowledge_base() -> KnowledgeBase:
    global _kb
    if _kb is None:
        _kb = KnowledgeBase()
    return _kb
