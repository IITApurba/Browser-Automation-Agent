"""Guardrail policy checks applied before every toolkit action executes."""

from __future__ import annotations

from urllib.parse import urlparse


class PolicyViolationError(Exception):
    """Raised when an action is blocked by policy; caught upstream and
    turned into a checkpointed error instead of crashing the run."""


DENIED_URL_SCHEMES = {"javascript", "data", "file"}
DENIED_SELECTOR_PATTERNS = ("script", "<script")


class ActionPolicy:
    def __init__(self, domain_allowlist: list[str] | None = None, allow_file_urls: bool = False) -> None:
        self.domain_allowlist = domain_allowlist
        self.allow_file_urls = allow_file_urls

    def check_navigate(self, url: str) -> None:
        parsed = urlparse(url)
        scheme = parsed.scheme.lower()

        if scheme == "file" and self.allow_file_urls:
            return

        if scheme in DENIED_URL_SCHEMES:
            raise PolicyViolationError(f"navigation to '{scheme}:' URLs is blocked by policy: {url!r}")

        if self.domain_allowlist is not None and scheme in ("http", "https"):
            if parsed.netloc not in self.domain_allowlist:
                raise PolicyViolationError(
                    f"navigation to domain '{parsed.netloc}' is not in the configured allowlist"
                )

    def check_type_text(self, text: str) -> None:
        lowered = text.lower()
        if any(pattern in lowered for pattern in DENIED_SELECTOR_PATTERNS):
            raise PolicyViolationError("blocked input text containing a disallowed script pattern")
