"""Atheris fuzz harness for the parsing code: zones files and event JSONL lines.

Run (Linux, x86_64; atheris has no other wheels):

    pip install --require-hashes -r requirements/fuzz.txt
    PYTHONPATH=src python fuzz/fuzz_events.py -dict=fuzz/events.dict -max_total_time=60 fuzz/corpus

Input layout, kept simple so seeds in ``fuzz/corpus`` can be written by hand:
byte 0 picks the target (odd: zones, even: events); for zones, bytes 1 and 2
set the depth array shape and the rest is the file; for events, the rest is
the file.

* zones: JSON text -> ``parse_zones``. Bad input must raise ``ValueError``
  (which the CLI reports as "bad zones file"), never anything else; accepted
  zones must satisfy the documented bounds and crop any depth array safely.
* events: bytes written as a daily JSONL file -> ``recent_events``,
  ``zone_state`` and ``camera_health``. Malformed lines are documented as
  skipped, so no file content may raise, and every result must still be
  JSON-serialisable (the MCP tools return ``json.dumps`` of it). The access
  log's ``result_count`` must accept every result, and ``camera_health``'s
  ``private`` must be a boolean or ``None`` whatever the ``privacy`` event says.

No camera and no depthai: only the pure modules are imported.
"""

from __future__ import annotations

import datetime as dt
import json
import math
import sys
import tempfile
from pathlib import Path

import atheris

with atheris.instrument_imports():
    import numpy as np

    from oak_events import mcp_server
    from oak_events.events import parse_zones

EVENTS_DIR = Path(tempfile.mkdtemp(prefix="oak-events-fuzz-"))
EVENTS_FILE = EVENTS_DIR / "2026-01-01.jsonl"
NOW = dt.datetime(2026, 1, 1, 12, 0, tzinfo=dt.timezone.utc)


def check_zones(data: bytes, shape: tuple[int, int]) -> None:
    try:
        spec = json.loads(data)
    except (ValueError, RecursionError):
        return  # not JSON: load_zones never gets this far
    try:
        zones = parse_zones(spec)
    except ValueError:
        return
    assert zones, "parse_zones returned no zones"
    names = [z.name for z in zones]
    assert len(names) == len(set(names)), names
    depth = np.full(shape, 1500, dtype=np.uint16)
    for z in zones:
        assert isinstance(z.name, str) and z.name
        if z.bbox is not None:
            x0, y0, x1, y1 = z.bbox
            assert 0.0 <= x0 < x1 <= 1.0 and 0.0 <= y0 < y1 <= 1.0, z.bbox
        for bound in (z.z_min_mm, z.z_max_mm):
            assert bound is None or math.isfinite(bound), (z.name, bound)
        if z.z_min_mm is not None and z.z_max_mm is not None:
            assert z.z_min_mm < z.z_max_mm
        crop = z.crop(depth)
        assert crop.ndim == 2 and crop.shape[0] <= shape[0] and crop.shape[1] <= shape[1]
        z.contains(1500.0, 0.5, 0.5)


def check_events(data: bytes) -> None:
    EVENTS_FILE.write_bytes(data)
    results = [
        mcp_server.recent_events(EVENTS_DIR, limit=50),
        mcp_server.recent_events(EVENTS_DIR, limit=5, kind="camera"),
        mcp_server.zone_state(EVENTS_DIR),
        mcp_server.camera_health(EVENTS_DIR, now=NOW),
    ]
    for result in results:
        json.dumps(result)
    for tool, result in zip(("recent_events", "recent_events", "zone_state", "camera_health"), results):
        assert mcp_server.result_count(tool, result) >= 0  # what the access log records
    assert results[3]["private"] in (True, False, None), results[3]["private"]
    assert results[3]["status"] in ("ok", "stale", "no_data") or results[3]["last_camera"] is not None


def test_one_input(data: bytes) -> None:
    if not data:
        return
    if data[0] & 1:
        shape = (data[1] % 40 + 1 if len(data) > 1 else 1, data[2] % 40 + 1 if len(data) > 2 else 1)
        check_zones(data[3:], shape)
    else:
        check_events(data[1:])


def main() -> None:
    atheris.Setup(sys.argv, test_one_input)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
