"""Startup privacy event, MCP access log, model hash check, confidence statistics."""

import asyncio
import hashlib
import io
import json
import math
import stat
import sys
import types

import pytest

from oak_events import camera, cli, mcp_server as m, privacy
from oak_events.events import ConfidenceStats, PersonTracker, Zone
from oak_events.sink import JsonlSink


def _events(stream: io.StringIO) -> list[dict]:
    return [json.loads(line) for line in stream.getvalue().splitlines()]


@pytest.fixture
def model(tmp_path):
    path = tmp_path / "model.tar.xz"
    path.write_bytes(b"not really a model archive")
    return path


@pytest.fixture
def private_env(monkeypatch):
    monkeypatch.delenv(privacy.OPT_IN_ENV, raising=False)
    for key, value in privacy.PRIVACY_ENV.items():
        monkeypatch.setenv(key, value)


# --------------------------------------------------------------------------- privacy event


def test_privacy_event_fields_private(private_env):
    assert privacy.event_fields() == {"private": True, "telemetry_opt_in": False, "deviations": []}


def test_privacy_event_fields_opted_in(monkeypatch):
    env = {privacy.OPT_IN_ENV: "1", "DEPTHAI_TELEMETRY": "1"}
    fields = privacy.event_fields(env)
    assert fields["private"] is False
    assert fields["telemetry_opt_in"] is True
    assert fields["deviations"] == sorted(privacy.PRIVACY_ENV)


def test_run_emits_privacy_event_before_depthai_loads(monkeypatch, model, private_env):
    def no_depthai():
        raise camera.CameraUnavailable("no depthai")

    monkeypatch.setattr(camera, "import_depthai", no_depthai)
    out = io.StringIO()
    with pytest.raises(camera.CameraUnavailable):
        camera.run(JsonlSink(stream=out), model=model)
    (ev,) = _events(out)
    assert ev["kind"] == "privacy"
    assert ev["private"] is True and ev["telemetry_opt_in"] is False


def test_run_privacy_event_shows_opt_in(monkeypatch, model):
    monkeypatch.setenv(privacy.OPT_IN_ENV, "1")
    monkeypatch.setenv("DEPTHAI_TELEMETRY", "1")
    monkeypatch.setattr(camera, "import_depthai", lambda: (_ for _ in ()).throw(camera.CameraUnavailable("x")))
    out = io.StringIO()
    with pytest.raises(camera.CameraUnavailable):
        camera.run(JsonlSink(stream=out), model=model)
    (ev,) = _events(out)
    assert ev["private"] is False and ev["telemetry_opt_in"] is True
    assert "DEPTHAI_TELEMETRY" in ev["deviations"]


def test_camera_health_reports_privacy_state(events_dir):
    from conftest import write_jsonl

    assert m.camera_health(events_dir)["private"] is None  # older event files have no privacy event
    write_jsonl(events_dir / "2026-01-03.jsonl", [
        {"ts": "2026-01-03T08:00:00+00:00", "kind": "privacy", "private": False, "telemetry_opt_in": True,
         "deviations": ["DEPTHAI_TELEMETRY"]},
    ])
    health = m.camera_health(events_dir)
    assert health["private"] is False
    assert health["last_privacy"]["telemetry_opt_in"] is True
    write_jsonl(events_dir / "2026-01-04.jsonl", [{"ts": "2026-01-04T08:00:00+00:00", "kind": "privacy",
                                                    "private": "yes"}])
    assert m.camera_health(events_dir)["private"] is None  # not a boolean: unknown, not private


# --------------------------------------------------------------------------- model hash


def test_file_sha256(model):
    assert camera.file_sha256(model, chunk_size=4) == hashlib.sha256(model.read_bytes()).hexdigest()


def test_model_sha256_mismatch_refuses_to_start(monkeypatch, model):
    monkeypatch.setattr(camera, "import_depthai", lambda: pytest.fail("depthai must not load on a hash mismatch"))
    out = io.StringIO()
    assert camera.run(JsonlSink(stream=out), model=model, model_sha256="0" * 64) == 3
    (ev,) = _events(out)
    assert ev["kind"] == "camera" and ev["state"] == "error"
    assert "SHA-256 mismatch" in ev["detail"]
    assert ev["model_sha256"] == hashlib.sha256(model.read_bytes()).hexdigest()
    assert ev["expected_sha256"] == "0" * 64
    assert str(model.parent) not in json.dumps(ev)  # file name only, no host paths in events


def test_model_sha256_match_continues(monkeypatch, model):
    loaded = []

    def no_depthai():
        loaded.append(True)
        raise camera.CameraUnavailable("no depthai")

    monkeypatch.setattr(camera, "import_depthai", no_depthai)
    digest = hashlib.sha256(model.read_bytes()).hexdigest().upper()  # case does not matter
    with pytest.raises(camera.CameraUnavailable):
        camera.run(JsonlSink(stdout=False), model=model, model_sha256=digest)
    assert loaded == [True]


@pytest.mark.parametrize("value", ["abc", "g" * 64, "0" * 63, "0" * 65])
def test_cli_rejects_malformed_model_sha256(value, model):
    with pytest.raises(SystemExit) as exc:
        cli.build_parser().parse_args(["run", "--model", str(model), "--model-sha256", value])
    assert exc.value.code == 2


def test_cli_mismatch_exit_code(model, capsys):
    assert cli.main(["run", "--model", str(model), "--model-sha256", "f" * 64]) == 3
    ev = json.loads(capsys.readouterr().out.strip())
    assert ev["state"] == "error" and "mismatch" in ev["detail"]


# --------------------------------------------------------------------------- fake camera run


def _fake_depthai(frames: list[list[tuple]], labels=("person",)):
    """Just enough of the DepthAI v3 API for camera.run: one device, detections, no depth frames."""
    remaining = list(frames)

    class Info:
        def getDeviceId(self):
            return "FAKE-DEVICE"

    class Device:
        @staticmethod
        def getAllAvailableDevices():
            return [Info()]

        def __init__(self, info):
            pass

        def setMaxReconnectionAttempts(self, n, cb):
            pass

        def getProductName(self):
            return "OAK-FAKE"

        def getBootloaderVersion(self):
            return None

    class Queue:
        def __init__(self, items):
            self.items = items

        def tryGet(self):
            return self.items.pop(0) if self.items else None

    class Node:
        def __init__(self):
            self.left = self.right = None
            self.out = self
            self.depth = types.SimpleNamespace(createOutputQueue=lambda **kw: Queue([]))

        def build(self, *args, **kwargs):
            return self

        def requestOutput(self, size):
            return types.SimpleNamespace(link=lambda target: None)

        def getClasses(self):
            return list(labels)

        def createOutputQueue(self, **kwargs):
            return Queue([_det(rows) for rows in remaining])

    def _det(rows):
        dets = []
        for label, conf, z, cx in rows:
            dets.append(types.SimpleNamespace(
                label=label, confidence=conf, spatialCoordinates=types.SimpleNamespace(x=0.0, y=0.0, z=z),
                xmin=cx - 0.05, xmax=cx + 0.05, ymin=0.45, ymax=0.55))
        return types.SimpleNamespace(detections=dets)

    class Pipeline:
        def __init__(self, device):
            self.loops = len(frames) + 1

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def create(self, cls):
            return Node()

        def start(self):
            pass

        def isRunning(self):
            self.loops -= 1
            return self.loops >= 0

    node = types.SimpleNamespace(Camera=object, StereoDepth=object, SpatialDetectionNetwork=object)
    sockets = types.SimpleNamespace(CAM_A="A", CAM_B="B", CAM_C="C")
    return types.SimpleNamespace(Device=Device, Pipeline=Pipeline, node=node, CameraBoardSocket=sockets,
                                 NNArchive=lambda path: path)


def test_camera_up_event_records_model_hash(monkeypatch, model, private_env):
    monkeypatch.setattr(camera, "import_depthai", lambda: _fake_depthai([]))
    out = io.StringIO()
    digest = hashlib.sha256(model.read_bytes()).hexdigest()
    assert camera.run(JsonlSink(stream=out), model=model, model_sha256=digest, discovery_timeout_s=0) == 1
    kinds = [e["kind"] for e in _events(out)]
    assert kinds == ["privacy", "camera", "camera"]
    up = _events(out)[1]
    assert up["state"] == "up" and up["model_sha256"] == digest and up["model_sha256_checked"] is True


def test_alive_events_carry_confidence_stats_only_when_enabled(monkeypatch, model):
    frames = [[(0, 0.9, 1500.0, 0.2), (0, 0.3, 1500.0, 0.2), (0, 0.7, 1500.0, 0.8)]] * 2
    zones = [Zone("left", (0.0, 0.0, 0.5, 1.0)), Zone("right", (0.5, 0.0, 1.0, 1.0))]
    for enabled in (False, True):
        monkeypatch.setattr(camera, "import_depthai", lambda: _fake_depthai(frames))
        out = io.StringIO()
        camera.run(JsonlSink(stream=out), model=model, zones=zones, alive_every_s=0.005, discovery_timeout_s=0,
                   confidence_stats=enabled)
        alive = [e for e in _events(out) if e["kind"] == "alive"]
        assert alive
        if not enabled:
            assert all("confidence" not in e for e in alive)
            continue
        total_left = sum(e["confidence"]["left"]["n"] for e in alive)
        below_left = sum(e["confidence"]["left"]["below"] for e in alive)
        assert (total_left, below_left) == (2, 2)
        assert sum(e["confidence"]["right"]["n"] for e in alive) == 2
        assert max(e["confidence"]["left"]["max"] or 0 for e in alive) == 0.9


# --------------------------------------------------------------------------- confidence statistics


def test_confidence_stats_snapshot_and_reset():
    s = ConfidenceStats()
    for conf, ok in ((0.6, True), (0.8, True), (0.2, False), (math.nan, True)):
        s.add(conf, ok)
    assert s.snapshot() == {"n": 2, "mean": 0.7, "min": 0.6, "max": 0.8, "below": 1}
    assert s.snapshot() == {"n": 0, "mean": None, "min": None, "max": None, "below": 0}


def test_tracker_stats_count_zone_and_label_only():
    stats = ConfidenceStats()
    t = PersonTracker(confirm_frames=1, zone=Zone("near", z_max_mm=2000), stats=stats)
    t.update([("person", 0.9, 0, 0, 1000), ("person", 0.4, 0, 0, 1000), ("person", 0.9, 0, 0, 3000),
              ("chair", 0.9, 0, 0, 1000)], now=0.0)
    assert stats.snapshot() == {"n": 1, "mean": 0.9, "min": 0.9, "max": 0.9, "below": 1}


def test_tracker_events_unchanged_by_stats():
    frames = [[("person", 0.9, 0, 0, 1000)], [("person", 0.4, 0, 0, 1000)], [("person", 0.8, 0, 0, 1000)]] * 3
    times = [i * 0.5 for i in range(len(frames))]
    frames.append([])
    times.append(30.0)
    plain, counted = PersonTracker(confirm_frames=2), PersonTracker(confirm_frames=2, stats=ConfidenceStats())
    for rows, now in zip(frames, times):
        a = [(e["kind"], e.get("dwell_s")) for e in plain.update(rows, now)]
        b = [(e["kind"], e.get("dwell_s")) for e in counted.update(rows, now)]
        assert a == b


# --------------------------------------------------------------------------- MCP access log


def test_access_log_records_keys_and_sizes_not_values(tmp_path):
    log = m.AccessLog(tmp_path / "audit" / "mcp-access.jsonl")
    entry = log.record("recent_events", {"limit": 50, "kind": "person_enter"}, 7)
    assert entry["kind"] == "mcp_access" and entry["tool"] == "recent_events"
    assert entry["args"] == {"kind": 12, "limit": 2}
    assert entry["result_count"] == 7 and entry["ok"] is True
    assert isinstance(entry["client_pid"], int)
    text = log.path.read_text(encoding="utf-8")
    assert "person_enter" not in text  # argument values are never written
    assert stat.S_IMODE(log.path.stat().st_mode) == 0o600


def test_call_tool_logs_counts_and_never_results(events_dir, tmp_path):
    log = m.AccessLog(tmp_path / "access.jsonl")
    text = m.call_tool("recent_events", lambda: m.recent_events(events_dir, limit=3), {"limit": 3, "kind": None}, log)
    assert len(json.loads(text)) == 3
    m.call_tool("zone_state", lambda: m.zone_state(events_dir), {}, log)
    m.call_tool("camera_health", lambda: m.camera_health(events_dir), {}, log)
    lines = [json.loads(line) for line in log.path.read_text(encoding="utf-8").splitlines()]
    assert [(e["tool"], e["result_count"]) for e in lines] == [("recent_events", 3), ("zone_state", 3),
                                                              ("camera_health", 2)]
    assert lines[0]["args"] == {"kind": 0, "limit": 1}
    assert "desk" not in log.path.read_text(encoding="utf-8")  # no event content in the audit log


def test_call_tool_logs_failures(tmp_path):
    log = m.AccessLog(tmp_path / "access.jsonl")

    def boom():
        raise OSError("disk gone")

    with pytest.raises(OSError):
        m.call_tool("zone_state", boom, {}, log)
    (entry,) = [json.loads(line) for line in log.path.read_text(encoding="utf-8").splitlines()]
    assert entry["ok"] is False and entry["error"] == "OSError" and entry["result_count"] is None


def test_call_tool_without_log_writes_nothing(events_dir, tmp_path):
    before = sorted(p.name for p in tmp_path.rglob("*"))
    m.call_tool("zone_state", lambda: m.zone_state(events_dir), {}, None)
    assert sorted(p.name for p in tmp_path.rglob("*")) == before


def test_access_log_must_be_outside_events_dir(events_dir, tmp_path):
    with pytest.raises(ValueError):
        m.check_access_log_path(events_dir, events_dir / "access.jsonl")
    with pytest.raises(ValueError):
        m.check_access_log_path(events_dir, tmp_path)  # a directory
    assert m.check_access_log_path(events_dir, tmp_path / "access.jsonl").name == "access.jsonl"


def test_cli_mcp_access_log(monkeypatch, events_dir, tmp_path, capsys):
    called = {}
    monkeypatch.setattr(m, "serve", lambda events_dir, **kw: called.update(kw))
    assert cli.main(["mcp", "--events-dir", str(events_dir), "--access-log", str(events_dir / "a.jsonl")]) == 2
    assert "outside the events directory" in capsys.readouterr().err
    assert cli.main(["mcp", "--events-dir", str(events_dir), "--access-log", str(tmp_path / "a.jsonl")]) == 0
    assert called["access_log"] == (tmp_path / "a.jsonl").resolve()
    called.clear()
    assert cli.main(["mcp", "--events-dir", str(events_dir)]) == 0
    assert "access_log" not in called  # off by default


def test_mcp_server_tools_write_access_log(events_dir, tmp_path):
    pytest.importorskip("mcp")
    log_path = tmp_path / "access.jsonl"
    server = m.build_server(events_dir, access_log=log_path)
    asyncio.run(server.call_tool("recent_events", {"limit": 2}))
    asyncio.run(server.call_tool("camera_health", {}))
    lines = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    assert [e["tool"] for e in lines] == ["recent_events", "camera_health"]
    assert lines[0]["result_count"] == 2


def test_mcp_server_without_access_log_writes_no_file(events_dir, tmp_path):
    pytest.importorskip("mcp")
    server = m.build_server(events_dir)
    asyncio.run(server.call_tool("zone_state", {}))
    assert not list(tmp_path.glob("*.jsonl"))
    assert sys.modules["oak_events.mcp_server"] is m
