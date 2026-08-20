import pytest

from packages.browser_tools.policy import ActionPolicy, PolicyViolationError


def test_blocks_javascript_url():
    policy = ActionPolicy()

    with pytest.raises(PolicyViolationError):
        policy.check_navigate("javascript:alert(1)")


def test_blocks_file_url_by_default():
    policy = ActionPolicy()

    with pytest.raises(PolicyViolationError):
        policy.check_navigate("file:///etc/passwd")


def test_allows_file_url_when_configured():
    policy = ActionPolicy(allow_file_urls=True)

    policy.check_navigate("file:///tmp/fixture.html")  # should not raise


def test_domain_allowlist_blocks_non_listed_domain():
    policy = ActionPolicy(domain_allowlist=["example.com"])

    with pytest.raises(PolicyViolationError):
        policy.check_navigate("https://evil.example.org/phish")


def test_domain_allowlist_allows_listed_domain():
    policy = ActionPolicy(domain_allowlist=["example.com"])

    policy.check_navigate("https://example.com/page")  # should not raise


def test_blocks_script_tag_in_input_text():
    policy = ActionPolicy()

    with pytest.raises(PolicyViolationError):
        policy.check_type_text("<script>alert(1)</script>")


def test_allows_ordinary_input_text():
    policy = ActionPolicy()

    policy.check_type_text("plain form input")  # should not raise
