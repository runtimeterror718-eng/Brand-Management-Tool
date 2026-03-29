"""
Cross-platform duplicate detection using MinHash LSH.
"""

from __future__ import annotations

import hashlib
import re
from datasketch import MinHash, MinHashLSH

# Global LSH index (rebuild on worker startup from DB if needed)
_lsh = MinHashLSH(threshold=0.7, num_perm=128)
_registered: set[str] = set()

NUM_PERM = 128


def _tokenize(text: str) -> list[str]:
    """Lowercase, strip URLs, split into word-level shingles (3-grams)."""
    text = re.sub(r"https?://\S+", "", text).lower()
    words = text.split()
    if len(words) < 3:
        return words
    return [" ".join(words[i : i + 3]) for i in range(len(words) - 2)]


def _make_minhash(tokens: list[str]) -> MinHash:
    m = MinHash(num_perm=NUM_PERM)
    for t in tokens:
        m.update(t.encode("utf-8"))
    return m


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.strip().lower().encode("utf-8")).hexdigest()


def is_duplicate(content_text: str, mention_id: str | None = None) -> bool:
    """Check if content is a near-duplicate of something already indexed."""
    if not content_text or not content_text.strip():
        return False

    c_hash = _content_hash(content_text)

    # Exact duplicate
    if c_hash in _registered:
        return True

    tokens = _tokenize(content_text)
    if not tokens:
        return False

    mh = _make_minhash(tokens)
    results = _lsh.query(mh)
    if results:
        return True

    # Not a duplicate — register it
    key = mention_id or c_hash
    try:
        _lsh.insert(key, mh)
    except ValueError:
        pass  # key already exists
    _registered.add(c_hash)
    return False


def reset_index() -> None:
    """Clear the LSH index (useful between test runs)."""
    global _lsh, _registered
    _lsh = MinHashLSH(threshold=0.7, num_perm=NUM_PERM)
    _registered = set()
