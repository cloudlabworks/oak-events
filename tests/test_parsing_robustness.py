"""Regressions for inputs the Atheris harness (fuzz/fuzz_events.py) found or targets."""

import datetime as dt
import json

import pytest

from oak_events import mcp_server as m
from oak_events.events import parse_zones
from oak_events.sink import JsonlSink

NOW = dt.datetime(2026, 1, 1, 12, 0, tzinfo=dt.timezone.utc)


def test_bad_utf8_line_is_skipped_not_fatal(tmp_path):
    good = json.dumps({"ts": "2026-01-01T11:59:00+00:00", "kind": "camera", "state": "up"}).encode()
    (tmp_path / "2026-01-01.jsonl").write_bytes(good + b"\n" + b'{"kind": "alive", "x": "\xe0\x80"}\n')
    # Before: UnicodeDecodeError from every tool, for the whole file.
    assert [e["kind"] for e in m.recent_events(tmp_path)] == ["camera"]
    assert m.camera_health(tmp_path, now=NOW)["status"] == "ok"


def test_line_separator_inside_a_field_does_not_split_the_event(tmp_path):
    # json.dumps(ensure_ascii=False) keeps U+2028 raw; str.splitlines() broke the line there.
    JsonlSink(out_dir=tmp_path, stdout=False).write(
        {"ts": "2026-01-01T11:00:00+00:00", "kind": "person_enter", "zone": "hall way", "count": 1})
    assert m.zone_state(tmp_path)["zones"]["hall way"]["person_present"] is True


@pytest.mark.parametrize("zone", [["a"], {"a": 1}, 5, True, None, ""])
def test_zone_state_skips_events_whose_zone_is_not_a_name(tmp_path, zone):
    line = {"ts": "2026-01-01T11:00:00+00:00", "kind": "person_enter", "zone": zone}
    (tmp_path / "2026-01-01.jsonl").write_text(json.dumps(line) + "\n", encoding="utf-8")
    assert m.zone_state(tmp_path) == {"zones": {}}  # before: TypeError (unhashable) for a list or dict


@pytest.mark.parametrize("ts", [5, ["2026-01-01"], {"t": 1}, "0001-01-01T00:00:00", "not a time"])
def test_camera_health_with_unreadable_timestamps(tmp_path, ts):
    line = {"ts": ts, "kind": "camera", "state": "up"}
    (tmp_path / "2026-01-01.jsonl").write_text(json.dumps(line) + "\n", encoding="utf-8")
    h = m.camera_health(tmp_path, now=NOW)
    if not isinstance(ts, str) or ts == "not a time":
        assert h["last_camera_age_s"] is None
    json.dumps(h)


@pytest.mark.parametrize("bad", ["NaN", "Infinity", "-Infinity", "1e400", "1" * 400])
def test_zones_reject_non_finite_and_oversized_numbers(bad):
    with pytest.raises(ValueError, match="z_mm"):
        parse_zones(json.loads(f'[{{"name": "a", "z_mm": [{bad}, null]}}]'))
    with pytest.raises(ValueError, match="bbox"):
        parse_zones(json.loads(f'[{{"name": "a", "bbox": [0, 0, 1, {bad}]}}]'))


def test_zones_still_accept_finite_numbers():
    zones = parse_zones({"zones": [{"name": "desk", "bbox": [0, 0.5, 1, 1.0], "z_mm": [400, 2500.5]}]})
    assert zones[0].z_min_mm == 400 and zones[0].z_max_mm == 2500.5
