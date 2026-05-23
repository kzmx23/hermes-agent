"""Tests for /title and /rename command aliases."""

from hermes_cli.commands import resolve_command


def test_rename_alias_resolves_to_title():
    cmd = resolve_command("rename")
    assert cmd is not None
    assert cmd.name == "title"


def test_slash_rename_alias_resolves_to_title():
    cmd = resolve_command("/rename")
    assert cmd is not None
    assert cmd.name == "title"
