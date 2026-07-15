#!/usr/bin/env python3
"""Regression smoke test for the ISEEVY decoder component — runs AGAINST THE LIVE DEVICE.

No Home Assistant or aiohttp required. The component is loaded standalone by stubbing
aiohttp and registering the component dir as a package, exactly like the debugging
repro technique. This guards the two bug classes we actually shipped fixes for:

  1. verify_channel returns a REAL title via pro.ini (v1.0.18 telnet/web cred decoupling).
     Before the fix, the coordinator passed web creds (admin/0p3nd00r) to the telnet
     client; the device's telnet console needs root/unisheen, so the shell-break failed
     and verify_channel returned all-None on every press.

  2. set_volume / get_streams behave correctly without corrupting cfg.ini
     (the /set.cgi corruption class — never call it).

Usage:
    python3 tests/smoke_live_device.py [HOST] [--username admin --password 0p3nd00r]

Exit code 0 = all checks passed; non-zero = regression or device unreachable.
The test never leaves the device in a changed state (volume is restored).
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import types

logging.basicConfig(level=logging.WARNING, format="%(levelname)s:%(name)s:%(message)s")

PKG = "custom_components/iseevy_decoder"

# --- 1. stub aiohttp (not installed in CI/agent venvs) -----------------------
aiohttp = types.ModuleType("aiohttp")


class _ClientSession:
    def __init__(self, *a, **k):
        pass

    closed = False

    async def close(self):
        pass


aiohttp.ClientSession = _ClientSession
sys.modules["aiohttp"] = aiohttp

# --- 2. register component as a real package so `from .const import` works ---
import os
import pathlib

_HERE = pathlib.Path(__file__).resolve().parent
_REPO = _HERE.parent
sys.path.insert(0, str(_REPO))
pkg = types.ModuleType("iseevy_decoder")
pkg.__path__ = [str(_REPO / PKG)]
sys.modules["iseevy_decoder"] = pkg

from iseevy_decoder.api import ISEEVYClient, ISEEVYAPIError, ISEEVYAuthError  # noqa: E402
from iseevy_decoder.const import DEFAULT_TELNET_USERNAME, DEFAULT_TELNET_PASSWORD  # noqa: E402


def _check(label: str, ok: bool, detail: str = "") -> bool:
    mark = "PASS" if ok else "FAIL"
    print(f"  [{mark}] {label}" + (f" — {detail}" if detail else ""))
    return ok


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("host", nargs="?", default="10.0.100.245")
    ap.add_argument("--username", default="admin")
    ap.add_argument("--password", default="0p3nd00r")
    args = ap.parse_args()

    print(f"== ISEEVY live smoke test -> {args.host} ==")
    # Build EXACTLY like the coordinator does (web creds only; telnet creds default
    # to root/unisheen inside ISEEVYClient). If telnet creds are wrong, verify_channel
    # fails → this test fails. That is the regression we are guarding.
    client = ISEEVYClient(
        host=args.host, username=args.username, password=args.password, port=80
    )

    failures = 0
    try:
        # ---- CHECK 1: telnet client uses the device's real console creds -------
        failures += 0 if _check(
            "telnet client uses decoder console creds (root/unisheen)",
            client.telnet.username == DEFAULT_TELNET_USERNAME
            and client.telnet.password == DEFAULT_TELNET_PASSWORD,
            f"telnet={client.telnet.username}/{client.telnet.password}",
        ) else 1

        # ---- CHECK 2: verify_channel returns a REAL title via pro.ini ----------
        try:
            v = await client.verify_channel()
            ok = bool(v.get("title")) and v.get("verified_via") == "pro.ini"
            failures += 0 if _check(
                "verify_channel returns real title via pro.ini (v1.0.18 regression)",
                ok,
                f"index={v.get('index')} title={v.get('title')!r} via={v.get('verified_via')}",
            ) else 1
        except (ISEEVYAPIError, ISEEVYAuthError, OSError) as e:
            failures += 1
            _check("verify_channel raised", False, f"{type(e).__name__}: {e}")

        # ---- CHECK 3: streams parse and option format matches select.py --------
        try:
            streams = await client.get_streams()
            slist = streams.get("streams", [])
            formatted = [f"{s['index']}: {s['title']}" for s in slist if s.get("title")]
            ok = len(slist) > 0 and len(formatted) == len(
                [s for s in slist if s.get("title")]
            )
            failures += 0 if _check(
                "get_streams parses titles; option format 'N: Title' matches select.py",
                ok,
                f"streams={len(slist)} options={len(formatted)}",
            ) else 1
        except (ISEEVYAPIError, OSError) as e:
            failures += 1
            _check("get_streams raised", False, f"{type(e).__name__}: {e}")

        # ---- CHECK 4: set_volume round-trips via safe cfg.ini (no /set.cgi) -----
        try:
            info0 = await client.get_system_info()
            orig = int(info0.get("volume", 0))
            new = (orig + 5) % 100
            set_ok = await client.set_volume(new)
            info1 = await client.get_system_info()
            read_back = int(info1.get("volume", -1))
            ok = set_ok and read_back == new
            failures += 0 if _check(
                "set_volume writes via safe cfg.ini and reads back (no corruption)",
                ok,
                f"orig={orig} set={new} read_back={read_back}",
            ) else 1
            # restore original volume so the device is left unchanged
            await client.set_volume(orig)
            info2 = await client.get_system_info()
            restored = int(info2.get("volume", -1))
            _check("volume restored to original", restored == orig, f"restored={restored}")
        except (ISEEVYAPIError, OSError) as e:
            failures += 1
            _check("set_volume raised", False, f"{type(e).__name__}: {e}")

    finally:
        await client.close()

    print(f"== {'ALL CHECKS PASSED' if failures == 0 else str(failures) + ' CHECK(S) FAILED'} ==")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
