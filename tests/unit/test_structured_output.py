import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from packages.agent.schemas import CriticVerdict
from packages.agent.structured_output import parse_with_retry


@pytest.mark.asyncio
async def test_parses_valid_json_on_first_try():
    llm = FakeListChatModel(responses=['{"passed": true, "reason": "ok", "should_replan": false}'])

    result = await parse_with_retry(llm, "judge this", CriticVerdict)

    assert result is not None
    assert result.passed is True


@pytest.mark.asyncio
async def test_recovers_from_malformed_json_via_retry():
    llm = FakeListChatModel(
        responses=[
            "not json at all",
            '{"passed": false, "reason": "recovered", "should_replan": true}',
        ]
    )

    result = await parse_with_retry(llm, "judge this", CriticVerdict)

    assert result is not None
    assert result.passed is False
    assert result.should_replan is True


@pytest.mark.asyncio
async def test_returns_none_when_still_invalid_after_retry():
    llm = FakeListChatModel(responses=["still not json", "still not json either"])

    result = await parse_with_retry(llm, "judge this", CriticVerdict)

    assert result is None


@pytest.mark.asyncio
async def test_strips_markdown_code_fences():
    llm = FakeListChatModel(responses=['```json\n{"passed": true, "reason": "fenced", "should_replan": false}\n```'])

    result = await parse_with_retry(llm, "judge this", CriticVerdict)

    assert result is not None
    assert result.reason == "fenced"
