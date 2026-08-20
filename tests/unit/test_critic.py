import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from packages.agent.nodes.critic import critic_node


def _base_state(**overrides):
    state = {
        "task_goal": "extract items",
        "plan": [{"type": "extract", "description": "extract items", "params": {}}],
        "current_subtask_index": 0,
        "last_action_result": {"status": "ok", "data": {"title": []}},
        "error": None,
        "captcha_detected": False,
        "retry_count": 0,
    }
    state.update(overrides)
    return state


@pytest.mark.asyncio
async def test_critic_passes_on_valid_verdict():
    llm = FakeListChatModel(responses=['{"passed": true, "reason": "looks right", "should_replan": false}'])

    state = await critic_node(_base_state(), llm=llm, toolkit=None)

    assert state["critic_verdict"]["passed"] is True
    assert state.get("error") is None


@pytest.mark.asyncio
async def test_critic_flags_should_replan_sets_error():
    llm = FakeListChatModel(responses=['{"passed": false, "reason": "empty extraction", "should_replan": true}'])

    state = await critic_node(_base_state(), llm=llm, toolkit=None)

    assert state["critic_verdict"]["passed"] is False
    assert "critic" in state["error"]


@pytest.mark.asyncio
async def test_critic_skips_when_worker_already_errored():
    llm = FakeListChatModel(responses=["irrelevant"])

    state = await critic_node(_base_state(error="worker: boom"), llm=llm, toolkit=None)

    assert state["critic_verdict"] is None
    assert state["error"] == "worker: boom"


@pytest.mark.asyncio
async def test_critic_defaults_to_pass_when_verdict_unparseable():
    llm = FakeListChatModel(responses=["not json", "still not json"])

    state = await critic_node(_base_state(), llm=llm, toolkit=None)

    assert state["critic_verdict"]["passed"] is True
    assert state.get("error") is None
