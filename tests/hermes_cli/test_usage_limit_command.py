"""Tests for /usage and /limit command aliases."""

from hermes_cli.commands import resolve_command


def test_limit_alias_resolves_to_usage():
    cmd = resolve_command("limit")
    assert cmd is not None
    assert cmd.name == "usage"


def test_slash_limit_alias_resolves_to_usage():
    cmd = resolve_command("/limit")
    assert cmd is not None
    assert cmd.name == "usage"
