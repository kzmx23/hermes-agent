"""Tests for account usage snapshots."""

from agent.account_usage import fetch_account_usage, render_account_usage_lines


def test_openai_account_usage_returns_clear_standard_api_caveat():
    snapshot = fetch_account_usage("openai", base_url="https://api.openai.com/v1", api_key="sk-test")

    assert snapshot is not None
    assert snapshot.provider == "openai"
    assert snapshot.unavailable_reason
    assert "standard inference API" in snapshot.unavailable_reason

    lines = render_account_usage_lines(snapshot)
    assert any("Provider: openai" in line for line in lines)
    assert any("standard inference API" in line for line in lines)
