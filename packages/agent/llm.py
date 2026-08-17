import os

from langchain_core.language_models.fake_chat_models import FakeListChatModel

FAKE_PLAN_RESPONSES = [
    """```json
{"subtasks": [
    {"type": "navigate", "description": "Go to listing page", "params": {"url": "file://LISTING_PATH"}},
    {"type": "extract", "description": "Extract listing items", "params": {"schema": {
        "title": {"selector": ".item .item-title", "attr": "text", "multiple": true},
        "price": {"selector": ".item .item-price", "attr": "text", "multiple": true}
    }}}
]}
```""",
    """{"subtasks": [{"type": "extract", "description": "Retry extraction", "params": {"schema": {}}}]}""",
]


def _fake_chat_model(overrides: dict | None = None):
    responses = (overrides or {}).get("responses", FAKE_PLAN_RESPONSES)
    return FakeListChatModel(responses=responses)


def get_chat_model(provider: str | None = None, overrides: dict | None = None):
    provider = provider or os.environ.get("LLM_PROVIDER", "openai")
    overrides = overrides or {}

    if provider == "fake":
        return _fake_chat_model(overrides)

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        api_key = overrides.get("api_key", os.environ.get("OPENAI_API_KEY"))
        model = overrides.get("model", os.environ.get("OPENAI_MODEL", "gpt-4o-mini"))
        return ChatOpenAI(api_key=api_key, model=model, temperature=0)

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        api_key = overrides.get("api_key", os.environ.get("ANTHROPIC_API_KEY"))
        model = overrides.get("model", os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5"))
        return ChatAnthropic(api_key=api_key, model=model, temperature=0)

    raise ValueError(f"Unknown LLM provider: {provider}")
