#!/usr/bin/env python3
"""End-to-end verification of the Codex null-output fix (commit 43a3f119f).

Replays the exact 27-May incident request through Hermes' real
`agent.codex_runtime.run_codex_stream` against the live (still-returning
output:null) chatgpt.com/backend-api/codex backend, using a minimal stub
agent. Asserts the stream parser's TypeError is now caught and the
response recovered from streamed output items.

Run with the gateway venv:
  HTTPS_PROXY=http://127.0.0.1:1081 \
  /home/max/.hermes/hermes-agent/venv/bin/python scripts/codex_fix_verify.py
"""
import os, sys, json, glob
from types import SimpleNamespace

HERMES_HOME = "/home/max/.hermes"
REPO = "/home/max/.hermes/hermes-agent"
os.environ.setdefault("HERMES_HOME", HERMES_HOME)
os.environ.setdefault("HTTPS_PROXY", "http://127.0.0.1:1081")
os.environ.setdefault("HTTP_PROXY", "http://127.0.0.1:1081")
sys.path.insert(0, REPO)

from openai import OpenAI
from agent.auxiliary_client import (
    _read_codex_access_token, _codex_cloudflare_headers, _CODEX_AUX_BASE_URL,
)
from agent.codex_runtime import run_codex_stream, _responses_null_output_iterable_error


class StubAgent:
    """Minimal agent surface that run_codex_stream touches."""
    def __init__(self):
        self._interrupt_requested = False
        self._codex_streamed_text_parts = []
        self.deltas = []
    def _ensure_primary_openai_client(self, reason=None):
        raise AssertionError("should not be called — client passed explicitly")
    def _touch_activity(self, *a, **k): pass
    def _fire_stream_delta(self, text): self.deltas.append(text)
    def _fire_reasoning_delta(self, text): pass
    def _client_log_context(self): return "(verify)"
    def _run_codex_create_stream_fallback(self, api_kwargs, client=None):
        raise AssertionError("fallback path hit — recovery from collected items failed")


def main():
    token = _read_codex_access_token()
    client = OpenAI(api_key=token, base_url=_CODEX_AUX_BASE_URL,
                    default_headers=_codex_cloudflare_headers(token))

    dump = json.load(open(sorted(glob.glob(f"{HERMES_HOME}/sessions/request_dump_20260527_004109_*.json"))[0]))
    body = dict(dump["request"]["body"])
    for k in ("extra_headers", "max_output_tokens", "stream"):
        body.pop(k, None)

    print("self-check: _responses_null_output_iterable_error detects the error:",
          _responses_null_output_iterable_error(TypeError("'NoneType' object is not iterable")))

    agent = StubAgent()
    print("→ calling run_codex_stream against live codex backend...")
    resp = run_codex_stream(agent, body, client=client)

    out = getattr(resp, "output", None)
    ok = isinstance(out, list) and len(out) > 0
    text = ""
    try:
        for item in out or []:
            for part in getattr(item, "content", []) or []:
                if getattr(part, "type", "") == "output_text":
                    text += getattr(part, "text", "")
    except Exception:
        pass
    print(f"  recovered output items: {len(out) if isinstance(out, list) else out}")
    print(f"  recovered text: {text!r}")
    print(f"  streamed deltas: {len(agent.deltas)}")
    print()
    if ok:
        print("✅ PASS: run_codex_stream RECOVERED from output:null (no crash). Fix works.")
    else:
        print("❌ FAIL: no recovered output.")
        sys.exit(1)


if __name__ == "__main__":
    main()
