import re
from collections import Counter

from packages.extraction.schemas import ExtractionSchema


class Extractor:
    """Thin wrapper validating a schema before delegating to BrowserToolkit.extract."""

    def __init__(self, toolkit) -> None:
        self._toolkit = toolkit

    async def extract(self, name: str, raw_schema: dict) -> dict:
        schema = ExtractionSchema.from_dict(name, raw_schema)
        return await self._toolkit.extract(schema.to_toolkit_dict())


def guess_schema_from_dom(dom_snapshot: str) -> dict:
    """Best-effort heuristic: find the most repeated class attribute and assume
    it marks list items, then guess a title-ish field. Not required to be smart.
    """
    class_matches = re.findall(r'class="([^"]+)"', dom_snapshot)
    tokens: Counter = Counter()
    for classes in class_matches:
        for cls in classes.split():
            tokens[cls] += 1

    repeated = [cls for cls, count in tokens.most_common() if count >= 2]
    if not repeated:
        return {}

    item_class = repeated[0]
    return {
        "item_text": {"selector": f".{item_class}", "attr": "text", "multiple": True},
    }
