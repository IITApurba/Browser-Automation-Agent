import json
import re

from pydantic import BaseModel, ValidationError

CORRECTION_SUFFIX = (
    "\n\nYour previous response failed schema validation with this error:\n{error}\n"
    "Return ONLY valid JSON matching the required shape, no prose, no markdown fences."
)


def _strip_code_fences(text: str) -> str:
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    return match.group(1) if match else text


async def _call(llm, prompt: str) -> str:
    response = await llm.ainvoke(prompt) if hasattr(llm, "ainvoke") else llm.invoke(prompt)
    return response.content if hasattr(response, "content") else str(response)


async def parse_with_retry(llm, prompt: str, schema: type[BaseModel]) -> BaseModel | None:
    """Call the LLM, validate the JSON response against `schema`.

    On a schema/parse failure, retries once with an error-correction prompt
    appended. Returns None (rather than raising) if the retry also fails, so
    callers can degrade to a checkpointed error instead of crashing.
    """
    raw = await _call(llm, prompt)
    last_error: Exception | None = None

    for attempt in range(2):
        try:
            cleaned = _strip_code_fences(raw).strip()
            data = json.loads(cleaned)
            return schema.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as exc:
            last_error = exc
            if attempt == 0:
                raw = await _call(llm, prompt + CORRECTION_SUFFIX.format(error=exc))

    return None
