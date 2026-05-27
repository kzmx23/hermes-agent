"""NeuralDeep STT — custom transcription provider plugin.

Registers an OpenAI-compatible Whisper backend (api.neuraldeep.ru) via the
upstream STT provider registry (PluginContext.register_transcription_provider).
Replaces the former hardcoded ``_transcribe_neuraldeep`` path in
tools/transcription_tools.py.

Activate with ``stt.provider: neuraldeep`` in config.yaml; needs
``NEURALDEEP_API_KEY`` (read from ~/.hermes/.env). Bundled here so both the
default gateway and named-profile gateways (sharing this checkout) discover it.
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional

from agent.transcription_provider import TranscriptionProvider

DEFAULT_BASE_URL = "https://api.neuraldeep.ru/v1"
DEFAULT_MODEL = "whisper-1"


def _env(key: str) -> Optional[str]:
    """Read an env value, preferring Hermes' .env-aware helper."""
    try:
        from tools.transcription_tools import get_env_value
        val = get_env_value(key)
        if val:
            return val
    except Exception:
        pass
    return os.getenv(key)


class NeuralDeepSTTProvider(TranscriptionProvider):
    @property
    def name(self) -> str:
        return "neuraldeep"

    @property
    def display_name(self) -> str:
        return "NeuralDeep (Whisper)"

    def is_available(self) -> bool:
        if not _env("NEURALDEEP_API_KEY"):
            return False
        try:
            import openai  # noqa: F401
        except Exception:
            return False
        return True

    def list_models(self):
        return [{"id": DEFAULT_MODEL, "display": "Whisper-1 (NeuralDeep)"}]

    def get_setup_schema(self) -> Dict[str, Any]:
        return {
            "name": "NeuralDeep (Whisper)",
            "badge": "paid",
            "tag": "OpenAI-compatible Whisper via api.neuraldeep.ru",
            "env_vars": [
                {
                    "key": "NEURALDEEP_API_KEY",
                    "prompt": "NeuralDeep API key",
                    "url": "https://api.neuraldeep.ru",
                },
            ],
        }

    def transcribe(
        self,
        file_path: str,
        *,
        model: Optional[str] = None,
        language: Optional[str] = None,
        **extra: Any,
    ) -> Dict[str, Any]:
        api_key = _env("NEURALDEEP_API_KEY")
        if not api_key:
            return {"success": False, "transcript": "",
                    "error": "NEURALDEEP_API_KEY not set", "provider": "neuraldeep"}
        try:
            from openai import OpenAI
        except Exception:
            return {"success": False, "transcript": "",
                    "error": "openai package not installed", "provider": "neuraldeep"}

        base_url = (_env("NEURALDEEP_STT_BASE_URL") or DEFAULT_BASE_URL).strip().rstrip("/")
        model_name = model or DEFAULT_MODEL
        try:
            client = OpenAI(api_key=api_key, base_url=base_url, timeout=60, max_retries=1)
            try:
                with open(file_path, "rb") as audio_file:
                    resp = client.audio.transcriptions.create(
                        model=model_name,
                        file=audio_file,
                        response_format="text" if model_name == "whisper-1" else "json",
                        **({"language": language} if language else {}),
                    )
                # NeuralDeep returns a JSON-shaped string even for
                # response_format="text"; reuse Hermes' normaliser.
                from tools.transcription_tools import _extract_transcript_text
                text = _extract_transcript_text(resp)
                return {"success": True, "transcript": text,
                        "provider": "neuraldeep"}
            finally:
                close = getattr(client, "close", None)
                if callable(close):
                    close()
        except Exception as exc:  # never raise — return the error envelope
            return {"success": False, "transcript": "",
                    "error": f"NeuralDeep STT failed: {exc}", "provider": "neuraldeep"}


def register(ctx):
    ctx.register_transcription_provider(NeuralDeepSTTProvider())
