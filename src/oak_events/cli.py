"""Command line: ``oak-events run | doctor | mcp``."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import math
import sys
from typing import Sequence

from . import __version__, privacy
from .events import load_zones
from .sink import JsonlSink

MIN_POE_BOOTLOADER = (0, 0, 29)


def _parse_version(text: str | None) -> tuple[int, ...] | None:
    if not text:
        return None
    parts = []
    for piece in text.strip().split("."):
        digits = "".join(ch for ch in piece if ch.isdigit())
        if not digits:
            break
        parts.append(int(digits))
    return tuple(parts) or None


def bootloader_advice(version: str | None) -> str:
    v = _parse_version(version)
    if v is None:
        return "unknown (device busy or already booted; stop other hosts and re-run doctor to read it)"
    if v < MIN_POE_BOOTLOADER:
        return ("older than 0.0.29: on RVC2 PoE devices, update the bootloader "
                "(fixes a device-not-found bug)")
    return "ok (>= 0.0.29)"


def _positive_seconds(value: str) -> float:
    try:
        seconds = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a number") from exc
    if not math.isfinite(seconds) or seconds <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return seconds


def cmd_run(args: argparse.Namespace) -> int:
    from . import camera  # lazy: imports privacy first, depthai only when running

    sink = JsonlSink(out_dir=args.out_dir, stdout=not args.quiet)
    try:
        zones = load_zones(args.zones)
    except (OSError, ValueError) as exc:
        print(f"oak-events: bad zones file: {exc}", file=sys.stderr)
        return 2
    try:
        return camera.run(
            sink,
            model=args.model,
            device_id=args.device_id,
            zones=zones,
            fps=args.fps,
            alive_every_s=args.alive_every,
            person_label=args.person_label,
            person_confidence=args.person_confidence,
            hold_seconds=args.hold_seconds,
        )
    except camera.CameraUnavailable as exc:
        print(f"oak-events: {exc}", file=sys.stderr)
        return 4
    except KeyboardInterrupt:
        sink.emit("camera", state="stopped")
        return 0
    except Exception as exc:  # noqa: BLE001  (the supervisor restarts us; the event says why)
        sink.emit("camera", state="error", detail=f"{type(exc).__name__}: {exc}"[:300])
        return 1


def cmd_doctor(args: argparse.Namespace) -> int:
    from . import camera

    report: dict[str, object] = {"oak_events": __version__, "python": sys.version.split()[0]}
    report["privacy"] = privacy.state()
    try:
        report["mcp"] = importlib.metadata.version("mcp")
    except importlib.metadata.PackageNotFoundError:
        report["mcp"] = None
    try:
        dai = camera.import_depthai()
    except camera.CameraUnavailable as exc:
        report["depthai"] = None
        report["devices"] = []
        report["hint"] = str(exc)
    else:
        report["depthai"] = getattr(dai, "__version__", "unknown")
        try:
            devices = camera.list_devices()
        except Exception as exc:  # noqa: BLE001
            devices = []
            report["device_error"] = f"{type(exc).__name__}: {exc}"
        for d in devices:
            d["bootloader_advice"] = bootloader_advice(d.get("bootloader"))
        report["devices"] = devices
        if not devices:
            report["hint"] = ("no devices visible. PoE cameras can take 30 s to a few minutes to free up after another host "
                              "exits; on macOS the process also needs local-network permission.")
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        _print_doctor(report)
    return 0


def _print_doctor(report: dict) -> None:
    p = report["privacy"]
    print(f"oak-events {report['oak_events']}  (python {report['python']})")
    print(f"depthai:  {report['depthai'] or 'not installed'}")
    print(f"mcp:      {report['mcp'] or 'not installed'}")
    print(f"privacy:  {'telemetry/crash dumps/auto-calibration OFF' if p['private'] else 'NOT fully private'}"
          f"{'  (opted in via ' + privacy.OPT_IN_ENV + '=1)' if p['opted_in_to_telemetry'] else ''}")
    for k, v in p["env"].items():
        print(f"  {k}={v}")
    devices = report.get("devices") or []
    print(f"devices:  {len(devices)}")
    for d in devices:
        print(f"  - {d['device_id']}  state={d['state']} protocol={d['protocol']} platform={d['platform']}")
        print(f"    bootloader={d.get('bootloader') or 'unknown'}: {d['bootloader_advice']}")
    if report.get("device_error"):
        print(f"device error: {report['device_error']}")
    if report.get("hint"):
        print(f"hint: {report['hint']}")


def cmd_mcp(args: argparse.Namespace) -> int:
    from . import mcp_server

    try:
        mcp_server.serve(args.events_dir, stale_after_s=args.stale_after)
    except RuntimeError as exc:
        print(f"oak-events: {exc}", file=sys.stderr)
        return 4
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="oak-events",
        description="Privacy-first events from Luxonis OAK cameras for AI agents. No pictures leave the camera.",
    )
    parser.add_argument("--version", action="version", version=f"oak-events {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="run the camera and emit JSON-line events")
    run.add_argument("--device-id", help="device id to open (default: first device found)")
    run.add_argument("--model", required=True,
                     help="path to a local detection NNArchive (.tar.xz); see README for fetching one once")
    run.add_argument("--out-dir", help="also append events to DIR/YYYY-MM-DD.jsonl")
    run.add_argument("--zones", help="zones JSON file (see examples/zones.example.json)")
    run.add_argument("--fps", type=float, default=10.0, help="detection frame rate (default 10)")
    run.add_argument("--alive-every", type=float, default=300.0, metavar="SECONDS",
                     help="heartbeat interval (default 300)")
    run.add_argument("--person-label", default="person", help="model class treated as a person (default person)")
    run.add_argument("--person-confidence", type=float, default=0.5, help="minimum confidence (default 0.5)")
    run.add_argument("--hold-seconds", type=float, default=60.0,
                     help="how long a depth change must persist before it is reported (default 60)")
    run.add_argument("--quiet", action="store_true", help="do not echo events to stdout")
    run.set_defaults(func=cmd_run)

    doctor = sub.add_parser("doctor", help="check depthai, devices, bootloader and privacy settings")
    doctor.add_argument("--json", action="store_true", help="machine-readable output")
    doctor.set_defaults(func=cmd_doctor)

    mcp = sub.add_parser("mcp", help="serve events to agents over MCP (stdio)")
    mcp.add_argument("--events-dir", required=True, help="directory written by 'run --out-dir'")
    mcp.add_argument("--stale-after", type=_positive_seconds, default=900.0, metavar="SECONDS",
                     help="mark camera health stale after this many seconds (default 900)")
    mcp.set_defaults(func=cmd_mcp)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
