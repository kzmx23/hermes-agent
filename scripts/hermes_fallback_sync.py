#!/usr/bin/env python3
"""Centralised Hermes fallback-chain management.

Hermes has NO shared/global fallback config — the terminal CLI and the
default gateway read ``~/.hermes/config.yaml`` while every named profile
(e.g. the Minecraft gateway) has its own independent
``~/.hermes/profiles/<name>/config.yaml``. This script keeps the
``fallback_providers`` chain identical across ALL of them in one shot,
and removes the legacy single-dict ``fallback_model`` key so there is a
single source of truth (matching hermes_cli.fallback_cmd._write_chain).

Format-preserving (ruamel round-trip): comments and key order are kept.

Usage:
  # show current chains everywhere
  python scripts/hermes_fallback_sync.py --check

  # write the canonical chain (CHAIN below) to every config, dry-run first
  python scripts/hermes_fallback_sync.py --dry-run
  python scripts/hermes_fallback_sync.py

  # override the chain inline (comma-separated provider/model pairs)
  python scripts/hermes_fallback_sync.py --set zai/glm-5.1,neuraldeep/qwen3.6-35b-a3b

After writing, restart the affected gateways:
  systemctl --user restart hermes-gateway.service hermes-gateway-egor-minecraft.service
"""
from __future__ import annotations

import argparse
import glob
import os
import sys
from pathlib import Path

from ruamel.yaml import YAML

HERMES_HOME = Path(os.path.expanduser(os.environ.get("HERMES_HOME_BASE", "~/.hermes")))

# Canonical fallback chain — edit here, or pass --set.
CHAIN: list[dict] = [
    {"provider": "zai", "model": "glm-5.1"},
    {"provider": "neuraldeep", "model": "qwen3.6-35b-a3b"},
]

yaml = YAML()
yaml.preserve_quotes = True


def config_paths() -> list[Path]:
    paths = [HERMES_HOME / "config.yaml"]
    paths += [Path(p) for p in sorted(glob.glob(str(HERMES_HOME / "profiles" / "*" / "config.yaml")))]
    return [p for p in paths if p.is_file()]


def fmt(chain) -> str:
    if not chain:
        return "(empty)"
    out = []
    for e in chain:
        if isinstance(e, dict):
            out.append(f"{e.get('provider')}/{e.get('model')}")
        else:
            out.append(f"!! bare:{e!r}")
    return " -> ".join(out)


def parse_set(arg: str) -> list[dict]:
    chain = []
    for pair in arg.split(","):
        pair = pair.strip()
        if not pair:
            continue
        provider, _, model = pair.partition("/")
        if not provider or not model:
            sys.exit(f"bad --set entry {pair!r}; expected provider/model")
        chain.append({"provider": provider.strip(), "model": model.strip()})
    return chain


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="report current chains, write nothing")
    ap.add_argument("--dry-run", action="store_true", help="show planned changes, write nothing")
    ap.add_argument("--set", dest="set_chain", help="override chain: provider/model,provider/model")
    args = ap.parse_args()

    chain = parse_set(args.set_chain) if args.set_chain else CHAIN
    paths = config_paths()
    if not paths:
        sys.exit(f"no config.yaml found under {HERMES_HOME}")

    print(f"Hermes home: {HERMES_HOME}")
    print(f"Canonical chain: {fmt(chain)}\n")

    changed = 0
    for p in paths:
        data = yaml.load(p.read_text())
        cur = data.get("fallback_providers")
        legacy = data.get("fallback_model")
        label = "default (cli+gateway)" if p == HERMES_HOME / "config.yaml" else f"profile:{p.parent.name}"
        print(f"• {label}  [{p}]")
        print(f"    current fallback_providers: {fmt(cur if isinstance(cur, list) else [])}"
              + ("" if not isinstance(cur, list) or all(isinstance(e, dict) for e in cur)
                 else "  ⚠ malformed (bare strings → disabled)"))
        if legacy:
            print(f"    legacy fallback_model: {legacy.get('provider')}/{legacy.get('model')}  ⚠ will be removed")

        if args.check:
            continue

        # Build the new chain (plain dicts; ruamel serialises as block style).
        data["fallback_providers"] = [dict(e) for e in chain]
        if "fallback_model" in data:
            del data["fallback_model"]

        if args.dry_run:
            print(f"    → would set: {fmt(chain)} (and drop legacy)")
        else:
            from io import StringIO
            buf = StringIO()
            yaml.dump(data, buf)
            p.write_text(buf.getvalue())
            print(f"    ✓ written: {fmt(chain)}")
            changed += 1
        print()

    if not args.check and not args.dry_run:
        print(f"Updated {changed} config file(s). Now restart gateways:")
        print("  systemctl --user restart hermes-gateway.service hermes-gateway-egor-minecraft.service")


if __name__ == "__main__":
    main()
