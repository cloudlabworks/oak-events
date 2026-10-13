import json
import sys

import pytest

from oak_events import cli


def test_help_lists_commands(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    for cmd in ("run", "doctor", "mcp"):
        assert cmd in out


def test_mcp_stale_after_defaults_and_accepts_positive_seconds():
    parser = cli.build_parser()
    default = parser.parse_args(["mcp", "--events-dir", "events"])
    custom = parser.parse_args(["mcp", "--events-dir", "events", "--stale-after", "60"])
    assert default.stale_after == 900.0
    assert custom.stale_after == 60.0


@pytest.mark.parametrize("value", ["0", "-1", "nan", "inf"])
def test_mcp_stale_after_rejects_non_positive_or_non_finite_values(value):
    with pytest.raises(SystemExit) as exc:
        cli.build_parser().parse_args(["mcp", "--events-dir", "events", "--stale-after", value])
    assert exc.value.code == 2


def test_cmd_mcp_passes_stale_after(monkeypatch, tmp_path):
    from oak_events import mcp_server

    called = {}
    monkeypatch.setattr(
        mcp_server,
        "serve",
        lambda events_dir, *, stale_after_s: called.update(
            events_dir=events_dir, stale_after_s=stale_after_s
        ),
    )
    assert cli.main(["mcp", "--events-dir", str(tmp_path), "--stale-after", "60"]) == 0
    assert called == {"events_dir": str(tmp_path), "stale_after_s": 60.0}


def test_doctor_without_depthai(monkeypatch, capsys):
    monkeypatch.setitem(sys.modules, "depthai", None)  # simulate "not installed"
    assert cli.main(["doctor", "--json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["depthai"] is None
    assert report["devices"] == []
    assert "oak-events[camera]" in report["hint"]
    assert report["privacy"]["private"] is True


def test_run_without_depthai_fails_cleanly(monkeypatch, tmp_path, capsys):
    monkeypatch.setitem(sys.modules, "depthai", None)
    model = tmp_path / "model.tar.xz"
    model.write_bytes(b"")
    assert cli.main(["run", "--model", str(model), "--quiet"]) == 4
    assert "oak-events[camera]" in capsys.readouterr().err


def test_run_with_missing_model_emits_event(tmp_path, capsys):
    rc = cli.main(["run", "--model", str(tmp_path / "missing.tar.xz")])
    assert rc == 3
    ev = json.loads(capsys.readouterr().out.strip())
    assert ev["kind"] == "camera" and ev["state"] == "error"
    assert str(tmp_path) not in ev["detail"]  # file name only, no host paths in events


def test_bootloader_advice():
    assert "older" in cli.bootloader_advice("0.0.28")
    assert cli.bootloader_advice("0.0.29").startswith("ok")
    assert cli.bootloader_advice("0.0.30").startswith("ok")
    assert cli.bootloader_advice(None).startswith("unknown")


def test_zones_file(tmp_path):
    from oak_events.events import load_zones

    p = tmp_path / "zones.json"
    p.write_text(json.dumps({"zones": [{"name": "door", "bbox": [0, 0, 0.5, 1]},
                                       {"name": "desk", "z_mm": [400, None]}]}))
    zones = load_zones(p)
    assert [z.name for z in zones] == ["door", "desk"]
    assert zones[1].z_min_mm == 400 and zones[1].z_max_mm is None
    assert [z.name for z in load_zones(None)] == ["view"]
