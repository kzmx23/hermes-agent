#!/usr/bin/env python3
"""Codex /responses reproduction for the 27-May-2026 gateway crash.

Replays the EXACT failing request body (captured in the incident
request_dump) against chatgpt.com/backend-api/codex with a fresh token,
to capture:
  (A) the raw HTTP status + raw SSE frames the server returns now, and
  (B) the full Python traceback if the OpenAI SDK's responses.stream()
      still raises `TypeError: 'NoneType' object is not iterable`.

Diagnostic only — makes at most two live Codex calls (output capped at
256 tokens). Does NOT modify any state. Run with the gateway venv:
  HTTPS_PROXY=http://127.0.0.1:1081 \
  /home/max/.hermes/hermes-agent/venv/bin/python scripts/codex_repro.py
"""
import os, sys, json, glob, base64, datetime, traceback

HERMES_HOME = "/home/max/.hermes"
REPO = "/home/max/.hermes/hermes-agent"
os.environ.setdefault("HERMES_HOME", HERMES_HOME)
# chatgpt.com is external -> route through the host main-proxy
os.environ.setdefault("HTTPS_PROXY", "http://127.0.0.1:1081")
os.environ.setdefault("HTTP_PROXY", "http://127.0.0.1:1081")
sys.path.insert(0, REPO)

from agent.auxiliary_client import (
    _read_codex_access_token,
    _codex_cloudflare_headers,
    _CODEX_AUX_BASE_URL,
)


def jwt_exp(tok):
    try:
        p = tok.split(".")[1]
        p += "=" * (-len(p) % 4)
        payload = json.loads(base64.urlsafe_b64decode(p))
        out = {}
        for k in ("exp", "iat"):
            if k in payload:
                out[k] = f"{payload[k]} = {datetime.datetime.utcfromtimestamp(payload[k])} UTC"
        return out
    except Exception as e:
        return {"decode_error": str(e)}


def main():
    token = _read_codex_access_token()
    if not token:
        print("NO CODEX TOKEN — _read_codex_access_token() returned empty")
        return
    print("=== TOKEN ===")
    print("  base_url:", _CODEX_AUX_BASE_URL)
    for k, v in jwt_exp(token).items():
        print(f"  {k}: {v}")
    print(f"  now    : {datetime.datetime.utcnow()} UTC")

    dumps = sorted(glob.glob(f"{HERMES_HOME}/sessions/request_dump_20260527_004109_*.json"))
    if not dumps:
        print("NO incident dump found")
        return
    dump = json.load(open(dumps[0]))
    body = dict(dump["request"]["body"])
    url = dump["request"]["url"]
    body.pop("extra_headers", None)        # internal kwarg, not a body field
    body.pop("max_output_tokens", None)    # codex backend rejects it (400)
    body["stream"] = True
    print(f"\n=== REPLAYING {os.path.basename(dumps[0])} ===")
    print("  url:", url)
    print("  body keys:", list(body.keys()),
          "| input items:", len(body.get("input", []) or []),
          "| tools:", len(body.get("tools", []) or []))

    headers = _codex_cloudflare_headers(token)
    headers["Authorization"] = f"Bearer {token}"
    headers["Content-Type"] = "application/json"

    # ---- (A) RAW capture: what does the server actually return? ----
    print("\n=== (A) RAW HTTP/SSE ===")
    import httpx
    try:
        with httpx.Client(timeout=40) as c:
            with c.stream("POST", url, json=body, headers=headers) as r:
                print("  HTTP status:", r.status_code)
                print("  resp content-type:", r.headers.get("content-type"))
                n = 0
                for line in r.iter_lines():
                    if line == "":
                        continue
                    print("  >", line[:280])
                    n += 1
                    if n >= 45:
                        print("  ... (truncated at 45 frames)")
                        break
                if n == 0:
                    print("  (empty body)")
    except Exception:
        print("  RAW request raised:")
        traceback.print_exc()

    # ---- (B) SDK path: reproduce the TypeError with full traceback ----
    print("\n=== (B) OpenAI SDK responses.stream() ===")
    from openai import OpenAI
    import openai as _openai
    print("  openai SDK version:", getattr(_openai, "__version__", "?"))
    client = OpenAI(api_key=token, base_url=_CODEX_AUX_BASE_URL,
                    default_headers=_codex_cloudflare_headers(token))
    sdk_keys = ("model", "input", "instructions", "tools", "reasoning",
                "include", "tool_choice", "parallel_tool_calls")
    sdk_params = {k: body[k] for k in sdk_keys if k in body}
    extra_body = {k: body[k] for k in ("store", "prompt_cache_key") if k in body}
    try:
        with client.responses.stream(extra_body=extra_body, **sdk_params) as s:
            evcount = 0
            for ev in s:
                evcount += 1
                if evcount <= 10:
                    print("  event:", getattr(ev, "type", type(ev).__name__))
            fr = s.get_final_response()
            out = getattr(fr, "output", "MISSING")
            print(f"  SDK OK — events={evcount}, final.output type={type(out).__name__}, "
                  f"status={getattr(fr,'status',None)}")
    except Exception:
        print("  SDK raised (this is the gateway's crash path):")
        traceback.print_exc()


if __name__ == "__main__":
    main()
