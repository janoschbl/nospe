#!/usr/bin/env python3
"""Phase-0-Verifikation: 64-bit Python, TWAIN DSM, Quellenliste.

Usage:
    uv run python scripts/verify_twain.py
    uv run python scripts/verify_twain.py --json

Exit codes: siehe docs/TWAIN_SETUP.md
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Backend-Root auf sys.path (scripts/ liegt unter backend/)
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from app.scanner.twain_env import probe_twain_environment, python_bitness  # noqa: E402
from app.scanner.twain_sources import get_twain_status  # noqa: E402


def _exit_code(env_ok: bool, bitness: int, dsm: bool, count: int) -> int:
    if bitness != 64:
        return 2
    if not env_ok and not dsm:
        return 1
    if not dsm:
        return 3
    if count == 0:
        return 4
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Nospe TWAIN 64-bit verification")
    parser.add_argument(
        "--json",
        action="store_true",
        help="JSON auf stdout (Meldungen/Hinweise weiterhin auf stderr bei Fehler)",
    )
    args = parser.parse_args()

    env = probe_twain_environment()
    status = get_twain_status()
    bitness = python_bitness()

    payload = {
        "platform": env.platform,
        "python_bitness": env.python_bitness,
        "twain_supported": env.twain_supported,
        "dsm_available": env.dsm_available,
        "pytwain_version": env.pytwain_version,
        "source_count": status.source_count,
        "sources": list(status.sources),
        "error": env.error,
        "hints": list(
            dict.fromkeys([*env.hints, *status.environment.hints])
        ),
        "ok": (
            bitness == 64
            and env.dsm_available
            and status.source_count > 0
            and not env.error
        ),
    }

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"Platform:        {env.platform}")
        print(f"Python:          {env.python_bitness}-bit")
        print(f"pytwain:         {env.pytwain_version or '—'}")
        print(f"DSM available:   {env.dsm_available}")
        print(f"TWAIN sources:   {status.source_count}")
        for name in status.sources:
            print(f"  - {name}")
        if env.error:
            print(f"Error:           {env.error}", file=sys.stderr)
        for hint in payload["hints"]:
            print(f"Hint:            {hint}", file=sys.stderr)

    code = _exit_code(
        env.twain_supported,
        bitness,
        env.dsm_available,
        status.source_count,
    )
    if code != 0 and not args.json:
        print(f"Exit code:       {code} (verification failed)", file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
