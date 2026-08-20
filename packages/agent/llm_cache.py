"""LLM response cache: exact-match (always on) + optional semantic layer.

Exact-match caches by a normalized-prompt hash — cheap, deterministic, safe
for tests. The semantic layer (cosine similarity over a bag-of-words local
embedding, no network call) is opt-in via `semantic=True` and only kicks in
on an exact-match miss.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import sqlite3
import time
from collections import Counter, OrderedDict
from dataclasses import dataclass


def _normalize(prompt: str) -> str:
    return re.sub(r"\s+", " ", prompt.strip().lower())


def _hash(prompt: str) -> str:
    return hashlib.sha256(_normalize(prompt).encode("utf-8")).hexdigest()


def _local_embedding(text: str) -> Counter:
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return Counter(tokens)


def _cosine(a: Counter, b: Counter) -> float:
    common = set(a) & set(b)
    dot = sum(a[t] * b[t] for t in common)
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


@dataclass
class CacheStats:
    hits: int = 0
    misses: int = 0
    semantic_hits: int = 0

    @property
    def total(self) -> int:
        return self.hits + self.misses

    @property
    def hit_rate(self) -> float:
        return self.hits / self.total if self.total else 0.0

    def as_dict(self) -> dict:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "semantic_hits": self.semantic_hits,
            "total": self.total,
            "hit_rate": round(self.hit_rate, 4),
        }


class LLMCache:
    def __init__(
        self,
        max_size: int = 256,
        semantic: bool = False,
        semantic_threshold: float = 0.92,
        persist_path: str | None = None,
    ) -> None:
        self.max_size = max_size
        self.semantic = semantic
        self.semantic_threshold = semantic_threshold
        self.stats = CacheStats()
        self._store: OrderedDict[str, dict] = OrderedDict()
        self._embeddings: dict[str, Counter] = {}
        self._persist_path = persist_path
        self._conn: sqlite3.Connection | None = None
        if persist_path:
            self._conn = sqlite3.connect(persist_path)
            self._conn.execute(
                "CREATE TABLE IF NOT EXISTS llm_cache (key TEXT PRIMARY KEY, prompt TEXT, response TEXT, ts REAL)"
            )
            self._conn.commit()
            self._load_from_disk()

    def _load_from_disk(self) -> None:
        assert self._conn is not None
        for key, prompt, response in self._conn.execute("SELECT key, prompt, response FROM llm_cache"):
            entry = {"prompt": prompt, "response": json.loads(response)}
            self._store[key] = entry
            if self.semantic:
                self._embeddings[key] = _local_embedding(prompt)

    def _persist(self, key: str, prompt: str, response) -> None:
        if self._conn is None:
            return
        self._conn.execute(
            "INSERT OR REPLACE INTO llm_cache (key, prompt, response, ts) VALUES (?, ?, ?, ?)",
            (key, prompt, json.dumps(response), time.time()),
        )
        self._conn.commit()

    def get(self, prompt: str) -> tuple[bool, object | None]:
        key = _hash(prompt)
        if key in self._store:
            self._store.move_to_end(key)
            self.stats.hits += 1
            return True, self._store[key]["response"]

        if self.semantic and self._embeddings:
            query_emb = _local_embedding(prompt)
            best_key, best_score = None, 0.0
            for cand_key, cand_emb in self._embeddings.items():
                score = _cosine(query_emb, cand_emb)
                if score > best_score:
                    best_key, best_score = cand_key, score
            if best_key is not None and best_score >= self.semantic_threshold:
                self.stats.hits += 1
                self.stats.semantic_hits += 1
                return True, self._store[best_key]["response"]

        self.stats.misses += 1
        return False, None

    def put(self, prompt: str, response) -> None:
        key = _hash(prompt)
        self._store[key] = {"prompt": prompt, "response": response}
        self._store.move_to_end(key)
        if self.semantic:
            self._embeddings[key] = _local_embedding(prompt)
        while len(self._store) > self.max_size:
            oldest_key, _ = self._store.popitem(last=False)
            self._embeddings.pop(oldest_key, None)
        self._persist(key, prompt, response)


# Rough per-1K-token USD costs for cost-savings reporting; not billing-accurate.
_COST_PER_1K_TOKENS = {
    "gpt-4o-mini": 0.00015,
    "claude-sonnet-4-5": 0.003,
    "fake": 0.0,
}


def estimate_cost(model: str, token_count: int) -> float:
    rate = _COST_PER_1K_TOKENS.get(model, 0.001)
    return round((token_count / 1000) * rate, 6)


class _FakeResponse:
    def __init__(self, content: str) -> None:
        self.content = content


class CachingChatModel:
    """Wraps any LangChain-style chat model (object with .ainvoke/.invoke
    returning a `.content`-bearing response) with the LLMCache above, and
    tracks token/cost totals for reporting. Drop-in replacement wherever a
    node calls `llm.ainvoke(prompt)`."""

    def __init__(self, inner, model_name: str = "fake", cache: LLMCache | None = None) -> None:
        self.inner = inner
        self.model_name = model_name
        self.cache = cache or LLMCache()
        self.call_count = 0
        self.total_tokens = 0
        self.total_cost = 0.0

    async def ainvoke(self, prompt: str):
        self.call_count += 1
        hit, cached = self.cache.get(prompt)
        if hit:
            return _FakeResponse(cached)

        response = await self.inner.ainvoke(prompt) if hasattr(self.inner, "ainvoke") else self.inner.invoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)

        token_count = max(1, len(prompt.split()) + len(content.split()))
        self.total_tokens += token_count
        self.total_cost += estimate_cost(self.model_name, token_count)

        self.cache.put(prompt, content)
        return _FakeResponse(content)

    def invoke(self, prompt: str):
        import asyncio

        return asyncio.get_event_loop().run_until_complete(self.ainvoke(prompt))

    def stats(self) -> dict:
        return {
            "call_count": self.call_count,
            "total_tokens": self.total_tokens,
            "total_cost_usd": round(self.total_cost, 6),
            "cache": self.cache.stats.as_dict(),
        }
