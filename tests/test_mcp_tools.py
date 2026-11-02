import asyncio
import datetime as dt
import json

import pytest

from oak_events import mcp_server as m


def test_recent_events_order_limit_and_kind(events_dir):
    evs = m.recent_events(events_dir, limit=3)
    assert [e["kind"] for e in evs] == ["person_enter", "depth_change", "alive"]
    assert evs[0]["zone"] == "desk"
    enters = m.recent_events(events_dir, kind="person_enter")
    assert [e["zone"] for e in enters] == ["door", "desk"]
    assert len(m.recent_events(events_dir, limit=1000)) == 7  # malformed line skipped
    assert m.recent_events(events_dir, limit=0)[-1]["kind"] == "alive"  # clamped to >= 1


def test_recent_events_missing_dir(tmp_path):
    assert m.recent_events(tmp_path / "nope") == []


def test_zone_state(events_dir):
    zones = m.zone_state(events_dir)["zones"]
    assert zones["door"]["person_present"] is False
    assert zones["door"]["person_event"]["kind"] == "person_exit"
    assert zones["desk"]["person_present"] is True
    assert zones["desk"]["person_event"]["nearest_mm"] == 900
    assert zones["view"]["person_present"] is False
    assert zones["view"]["last_depth_change"]["cells"] == ["r1c2"]
    assert zones["view"]["depth_baseline"]["cells_judged"] == 44


def test_camera_health_ok_and_stale(events_dir):
    soon = dt.datetime(2026, 1, 2, 10, 6, tzinfo=dt.timezone.utc)
    h = m.camera_health(events_dir, now=soon)
    assert h["status"] == "ok"
    assert h["last_camera"]["state"] == "up"
    assert h["last_alive_age_s"] == 60.0
    later = soon + dt.timedelta(hours=2)
    assert m.camera_health(events_dir, now=later)["status"] == "stale"


def test_camera_health_reports_failure_state(tmp_path):
    from conftest import write_jsonl

    write_jsonl(tmp_path / "2026-01-03.jsonl", [
        {"ts": "2026-01-03T10:00:00+00:00", "kind": "alive", "det_fps": 10.0, "person": False, "occupied": []},
        {"ts": "2026-01-03T10:01:00+00:00", "kind": "camera", "state": "error", "detail": "RuntimeError: x"},
    ])
    now = dt.datetime(2026, 1, 3, 10, 2, tzinfo=dt.timezone.utc)
    assert m.camera_health(tmp_path, now=now)["status"] == "error"
    assert m.camera_health(tmp_path / "empty", now=now)["status"] == "no_data"


def test_tool_outputs_are_json_text(events_dir):
    for result in (m.recent_events(events_dir), m.zone_state(events_dir), m.camera_health(events_dir)):
        json.dumps(result)


def test_mcp_server_registers_text_tools(events_dir):
    pytest.importorskip("mcp")
    server = m.build_server(events_dir, stale_after_s=60)
    tools = asyncio.run(server.list_tools())
    names = sorted(t.name for t in tools)
    assert names == ["camera_health", "recent_events", "zone_state"]
