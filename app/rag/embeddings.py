from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from collections.abc import Iterable

TOKEN_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")

STOP_WORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "can",
        "do",
        "for",
        "from",
        "has",
        "have",
        "how",
        "i",
        "if",
        "in",
        "is",
        "it",
        "me",
        "my",
        "of",
        "on",
        "or",
        "our",
        "that",
        "the",
        "their",
        "this",
        "to",
        "we",
        "what",
        "when",
        "where",
        "which",
        "who",
        "with",
        "you",
    }
)

TOKEN_ALIASES = {
    "abroad": "international",
    "annual": "pto",
    "computer": "equipment",
    "holiday": "pto",
    "holidays": "pto",
    "laptop": "equipment",
    "overseas": "international",
    "reimburse": "expense",
    "reimbursed": "expense",
    "reimbursement": "expense",
    "reimbursements": "expense",
    "vacation": "pto",
}

PHRASE_EXPANSIONS = {
    "another country": ("international", "out-of-jurisdiction"),
    "outside canada": ("international", "out-of-jurisdiction"),
    "outside the country": ("international", "out-of-jurisdiction"),
    "work abroad": ("international", "remote", "out-of-jurisdiction"),
    "work from home": ("remote", "home-office"),
    "week off": ("pto", "leave"),
    "time off": ("pto", "leave"),
    "paid leave": ("pto", "leave"),
    "report harassment": ("conduct", "case", "escalation"),
}


def tokenize(text: str) -> list[str]:
    normalized = text.casefold()
    expanded: list[str] = []
    for phrase, additions in PHRASE_EXPANSIONS.items():
        if phrase in normalized:
            expanded.extend(additions)
    tokens = []
    for token in TOKEN_PATTERN.findall(normalized):
        if token in STOP_WORDS:
            continue
        tokens.append(TOKEN_ALIASES.get(token, token))
    return tokens + expanded


class LocalHashEmbedding:
    """A deterministic, dependency-free local text embedding.

    Word and adjacent-token features are projected into a fixed dense space using
    feature hashing. Domain aliases provide limited semantic normalization. The model
    is intentionally small enough for deterministic CI and free-tier deployment.
    """

    name = "peopleops-local-hash-v2"

    def __init__(self, dimensions: int = 384) -> None:
        if dimensions < 64:
            raise ValueError("embedding dimensions must be at least 64")
        self.dimensions = dimensions

    def embed(self, text: str) -> tuple[float, ...]:
        tokens = tokenize(text)
        features = list(tokens)
        features.extend(
            f"{left}::{right}" for left, right in zip(tokens, tokens[1:], strict=False)
        )
        counts = Counter(features)
        vector = [0.0] * self.dimensions
        for feature, count in counts.items():
            digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
            bucket = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] & 1 else -1.0
            vector[bucket] += sign * (1.0 + math.log(count))
        magnitude = math.sqrt(sum(value * value for value in vector))
        if magnitude:
            vector = [value / magnitude for value in vector]
        return tuple(round(value, 8) for value in vector)


def cosine_similarity(left: Iterable[float], right: Iterable[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))
