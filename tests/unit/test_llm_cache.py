from packages.agent.llm_cache import LLMCache, estimate_cost


def test_exact_match_hit_on_normalized_prompt():
    cache = LLMCache()
    cache.put("Hello   World", "response-a")

    hit, value = cache.get("hello world")

    assert hit is True
    assert value == "response-a"
    assert cache.stats.hits == 1


def test_miss_when_prompt_unseen():
    cache = LLMCache()

    hit, value = cache.get("never cached")

    assert hit is False
    assert value is None
    assert cache.stats.misses == 1


def test_semantic_layer_matches_similar_prompt_above_threshold():
    cache = LLMCache(semantic=True, semantic_threshold=0.5)
    cache.put("extract the product title and price from the page", "response-a")

    hit, value = cache.get("extract product title price from page")

    assert hit is True
    assert value == "response-a"
    assert cache.stats.semantic_hits == 1


def test_semantic_layer_off_by_default_falls_back_to_exact_only():
    cache = LLMCache(semantic=False)
    cache.put("extract the product title and price from the page", "response-a")

    hit, value = cache.get("extract product title price from page")

    assert hit is False
    assert value is None


def test_lru_eviction_respects_max_size():
    cache = LLMCache(max_size=2)
    cache.put("a", "1")
    cache.put("b", "2")
    cache.put("c", "3")

    hit_a, _ = cache.get("a")
    hit_c, _ = cache.get("c")

    assert hit_a is False
    assert hit_c is True


def test_estimate_cost_known_and_unknown_model():
    assert estimate_cost("fake", 1000) == 0.0
    assert estimate_cost("gpt-4o-mini", 1000) == 0.00015
    assert estimate_cost("some-unlisted-model", 1000) == 0.001
