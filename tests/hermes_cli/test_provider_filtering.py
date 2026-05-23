"""Tests for Maxim's active-provider filtering in model pickers."""


def test_canonical_providers_only_include_maxim_active_allowlist():
    from hermes_cli.models import CANONICAL_PROVIDERS

    slugs = {p.slug for p in CANONICAL_PROVIDERS}
    assert "zai" in slugs
    assert "openai-codex" in slugs
    assert "gemini" in slugs
    assert "kimi-coding" in slugs
    assert "minimax" in slugs
    assert "deepseek" in slugs

    # Known noisy/unwanted providers must not appear in CLI/gateway picker catalogs.
    assert "anthropic" not in slugs
    assert "copilot" not in slugs
    assert "copilot-acp" not in slugs
    assert "minimax-oauth" not in slugs
    assert "minimax-cn" not in slugs
    assert "kimi-coding-cn" not in slugs


def test_filter_to_canonical_providers_keeps_user_defined_and_drops_noncanonical():
    from hermes_cli.model_switch import _filter_to_canonical_providers

    rows = [
        {"slug": "zai", "name": "Z.AI", "is_user_defined": False},
        {"slug": "anthropic", "name": "Anthropic", "is_user_defined": False},
        {"slug": "cliproxy", "name": "Cliproxy", "is_user_defined": True},
        {"slug": "neuraldeep", "name": "NeuralDeep", "is_user_defined": True},
    ]
    filtered = _filter_to_canonical_providers(rows)
    slugs = [r["slug"] for r in filtered]

    assert slugs == ["zai", "cliproxy", "neuraldeep"]
