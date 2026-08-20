"""Minimal OpenTelemetry-shaped tracing: no external SDK dependency.

Each Span carries trace_id/span_id/name/start/end/attributes, matching the
shape OTel exporters expect, so swapping in the real `opentelemetry-sdk`
later is a matter of changing `emit()`, not the call sites.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field

logger = logging.getLogger("agent.tracing")

_CURRENT_TRACE_ID: str | None = None


@dataclass
class Span:
    name: str
    trace_id: str
    span_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    start_ns: int = field(default_factory=time.perf_counter_ns)
    end_ns: int | None = None
    attributes: dict = field(default_factory=dict)

    @property
    def duration_ms(self) -> float:
        end = self.end_ns if self.end_ns is not None else time.perf_counter_ns()
        return (end - self.start_ns) / 1_000_000

    def set_attribute(self, key: str, value) -> None:
        self.attributes[key] = value

    def emit(self) -> None:
        record = {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "name": self.name,
            "duration_ms": round(self.duration_ms, 3),
            "attributes": self.attributes,
        }
        logger.info(json.dumps(record))


def new_trace_id(run_id: str | None = None) -> str:
    global _CURRENT_TRACE_ID
    _CURRENT_TRACE_ID = run_id or uuid.uuid4().hex
    return _CURRENT_TRACE_ID


@contextmanager
def span(name: str, trace_id: str | None = None, **attributes):
    s = Span(name=name, trace_id=trace_id or _CURRENT_TRACE_ID or uuid.uuid4().hex, attributes=dict(attributes))
    try:
        yield s
    finally:
        s.end_ns = time.perf_counter_ns()
        s.emit()


def wrap_node(node_fn, node_name: str):
    """Wrap a LangGraph node coroutine so every invocation emits a span."""

    async def _wrapped(state, *args, **kwargs):
        run_id = state.get("run_id") if isinstance(state, dict) else None
        with span(node_name, trace_id=run_id, run_id=run_id) as s:
            result = await node_fn(state, *args, **kwargs)
            if isinstance(result, dict):
                s.set_attribute("retry_count", result.get("retry_count"))
                s.set_attribute("error", bool(result.get("error")))
            return result

    _wrapped.__name__ = getattr(node_fn, "__name__", node_name)
    return _wrapped
