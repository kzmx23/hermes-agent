"""Tests to verify that CLI lists recent sessions with order_by_last_active=True."""

from unittest.mock import MagicMock, patch
import pytest


def test_cli_list_recent_sessions_orders_by_last_active():
    from cli import HermesCLI

    # We mock _make_cli behavior or construct HermesCLI directly with patch mocks
    with patch("cli.get_tool_definitions", return_value=[]):
        cli = HermesCLI()
        cli._session_db = MagicMock()
        cli._session_db.list_sessions_rich.return_value = []

        cli._list_recent_sessions(limit=5)

        cli._session_db.list_sessions_rich.assert_called_once_with(
            source="cli",
            exclude_sources=["tool"],
            limit=5,
            order_by_last_active=True,
        )
