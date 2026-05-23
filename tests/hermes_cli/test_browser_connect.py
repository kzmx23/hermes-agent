"""Tests for hermes_cli/browser_connect.py."""

from hermes_cli.browser_connect import _chrome_debug_args


def test_chrome_debug_args_include_no_sandbox():
    args = _chrome_debug_args(9222)
    assert "--no-sandbox" in args
