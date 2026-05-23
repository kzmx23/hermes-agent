"""Tests for gateway voice transcription enrichment."""

import asyncio
from types import SimpleNamespace
from unittest.mock import patch

import pytest


@pytest.fixture
def gateway_runner():
    from gateway.run import GatewayRunner

    class _Stub:
        config = SimpleNamespace(stt_enabled=True)
        _enrich_message_with_transcription = GatewayRunner._enrich_message_with_transcription

        def _has_setup_skill(self):
            return False

    return _Stub()


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class TestEnrichMessageWithTranscription:
    def test_successful_transcript_uses_compact_voice_prefix(self, gateway_runner):
        with patch(
            "tools.transcription_tools.transcribe_audio",
            return_value={"success": True, "transcript": "Привет, это голосовое."},
        ):
            out = _run(gateway_runner._enrich_message_with_transcription("", ["/tmp/voice.ogg"]))

        assert out == "🎤 [Voice] Привет, это голосовое."
        assert "The user sent a voice message" not in out
