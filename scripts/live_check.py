"""Check the integration's API client against the real Envi cloud and heaters.

Reads credentials from ENVI_USERNAME / ENVI_PASSWORD, or prompts for them.
Nothing is printed or stored that includes the password or the auth token.

Default is read-only. With --write, each heater's current target temperature
is sent back to it unchanged, which exercises the same update endpoint Home
Assistant uses without changing what the heater does.

With --dump, the full raw API responses (device list, every heater's state,
schedules) are written to api_dump.json in the repo root, with personal
fields such as serial numbers, WiFi names, MAC/IP addresses and coordinates
blanked out. The file is git-ignored.
"""
from __future__ import annotations

import argparse
import asyncio
import getpass
import json
import os
from pathlib import Path
import sys
import time

import aiohttp

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from custom_components.smart_envi.api import (  # noqa: E402
    EnviApiClient,
    EnviApiError,
    EnviAuthenticationError,
)
from custom_components.smart_envi.const import ENDPOINTS  # noqa: E402

OK = "  ok  "
FAIL = "  FAIL"

DUMP_PATH = Path(__file__).resolve().parent.parent / "api_dump.json"
# Keys whose values are personal or identifying. Long fragments match anywhere
# in the key; short ones only as a whole word (so "lat" hits "lat" but not "relative").
SENSITIVE_FRAGMENTS = (
    "serial", "ssid", "email", "phone", "password", "token", "secret",
    "latitude", "longitude", "address", "postal", "owner", "account", "network",
    "wifi_name",
)
SENSITIVE_WORDS = {"mac", "ip", "lat", "lng", "lon", "long", "zip", "user", "uid"}


def _is_sensitive(key: str) -> bool:
    k = key.lower()
    words = set(k.replace("-", "_").split("_"))
    return any(f in k for f in SENSITIVE_FRAGMENTS) or bool(words & SENSITIVE_WORDS)


def _redact(value, key: str = ""):
    """Blank out personal values while keeping the structure and types visible."""
    if isinstance(value, dict):
        return {kk: _redact(v, kk) for kk, v in value.items()}
    if isinstance(value, list):
        return [_redact(v, key) for v in value]
    if key and _is_sensitive(key) and value not in (None, "", [], {}):
        return f"<redacted {type(value).__name__}>"
    if isinstance(value, str) and "@" in value:
        return "<redacted str>"
    return value


async def main(username: str, password: str, write: bool, dump: bool) -> int:
    failures = 0
    raw: dict = {"device_list": None, "devices": {}, "schedules": None}

    async with aiohttp.ClientSession() as session:
        client = EnviApiClient(session, username, password)

        start = time.monotonic()
        try:
            await client.authenticate()
        except EnviAuthenticationError as err:
            print(f"{FAIL} login: {err.__cause__ or err}")
            return 1
        print(f"{OK} login ({time.monotonic() - start:.1f}s), token valid until "
              f"{client.token_expires:%Y-%m-%d %H:%M} UTC")

        if dump:
            raw["device_list"] = await client._request("GET", ENDPOINTS["device_list"])
        device_ids = await client.fetch_all_device_ids()
        print(f"{OK} device list: {len(device_ids)} heater(s)")

        for device_id in device_ids:
            try:
                d = await client.get_device_state(device_id)
                if dump:
                    raw["devices"][f"heater_{len(raw['devices']) + 1}"] = await client._request(
                        "GET", ENDPOINTS["device_get"].format(device_id=device_id)
                    )
            except EnviApiError as err:
                print(f"{FAIL} heater {device_id}: {err}")
                failures += 1
                continue
            unit = d.get("temperature_unit", "?")
            print(
                f"{OK} {d.get('name', device_id)!r}: "
                f"{'ON' if d.get('state') == 1 else 'OFF'}, "
                f"room {d.get('ambient_temperature')}°{unit}, "
                f"target {d.get('current_temperature')}°{unit}, "
                f"mode {d.get('current_mode')}, "
                f"online={d.get('status') == 1}, "
                f"model {d.get('model_no')}, fw {d.get('firmware_version')}"
            )

            if write:
                target = d.get("current_temperature")
                if target is None:
                    print(f"{FAIL}   write skipped: no target temperature reported")
                    failures += 1
                    continue
                try:
                    await client.set_temperature(device_id, target)
                    after = await client.get_device_state(device_id)
                    same = after.get("current_temperature") == target
                    print(f"{OK if same else FAIL}   write: re-sent target {target}°{unit}, "
                          f"heater now reports {after.get('current_temperature')}°{unit}")
                    failures += 0 if same else 1
                except EnviApiError as err:
                    print(f"{FAIL}   write: {err}")
                    failures += 1

        try:
            schedules = await client.get_schedule_list()
            if dump:
                raw["schedules"] = await client._request("GET", ENDPOINTS["schedule_list"])
            print(f"{OK} schedules: {len(schedules)}")
            for s in schedules:
                events = sum(len(g.get("events", [])) for g in s.get("schedule_data", []) or [])
                print(f"        - {s.get('name') or 'Unnamed'!r} (heater {s.get('device_id')}): {events} event(s)")
        except EnviApiError as err:
            print(f"{FAIL} schedules: {err}")
            failures += 1

    if dump:
        DUMP_PATH.write_text(json.dumps(_redact(raw), indent=2, sort_keys=True), encoding="utf-8")
        print(f"\nRaw API responses (personal fields redacted) written to {DUMP_PATH.name}")

    print(f"\n{'All checks passed' if not failures else f'{failures} check(s) failed'}")
    return 1 if failures else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--write", action="store_true",
                        help="re-send each heater's current target temperature (no physical change)")
    parser.add_argument("--dump", action="store_true",
                        help="save raw API responses, with personal fields redacted, to api_dump.json")
    args = parser.parse_args()
    username = os.environ.get("ENVI_USERNAME") or input("Envi email: ")
    password = os.environ.get("ENVI_PASSWORD") or getpass.getpass("Envi password: ")
    sys.exit(asyncio.run(main(username, password, args.write, args.dump)))
