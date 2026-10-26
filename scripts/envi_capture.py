"""mitmproxy add-on that records the Envi app's API calls, and nothing else.

Used to find endpoints the integration doesn't know yet (such as saving a
schedule) by watching what the official Envi app sends. Run with:

    mitmdump -s scripts/envi_capture.py

Only requests to *.enviliving.com are recorded; all other traffic passes
through untouched and unlogged. Passwords and auth tokens are blanked before
anything is written. Each call is appended as one JSON line to
api_capture.jsonl in the repo root (git-ignored) and summarised on screen.
"""
from __future__ import annotations

import json
from pathlib import Path
import time

from mitmproxy import http

OUT = Path(__file__).resolve().parent.parent / "api_capture.jsonl"
SECRET_KEYS = {"password", "token", "access_token", "refresh_token", "authorization"}


def _scrub(value):
    if isinstance(value, dict):
        return {k: "<redacted>" if k.lower() in SECRET_KEYS else _scrub(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_scrub(v) for v in value]
    return value


def _body(message: http.Message):
    if not message.content:
        return None
    try:
        return _scrub(json.loads(message.content))
    except (ValueError, UnicodeDecodeError):
        return f"<{len(message.content)} bytes, not JSON>"


def response(flow: http.HTTPFlow) -> None:
    if not flow.request.pretty_host.endswith("enviliving.com"):
        return
    record = {
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "method": flow.request.method,
        "path": flow.request.path,
        "request": _body(flow.request),
        "status": flow.response.status_code if flow.response else None,
        "response": _body(flow.response) if flow.response else None,
    }
    with OUT.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
    print(f"[envi] {record['method']:6} {record['status']} {record['path']}")
