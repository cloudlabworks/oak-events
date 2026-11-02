"""MCP stdio server: text-only tools over the JSONL event files.

The server reads the files written by ``oak-events run --out-dir DIR``. It
never opens the camera and has no way to return a picture: every tool returns
JSON text built from event lines.

The tool logic lives in plain functions (``recent_events``, ``zone_state``,
``camera_health``) so it can be used and tested without the ``mcp`` package;
``build_server`` wraps them with FastMCP from the official MCP Python SDK
(``MCPServer`` in mcp 2.x, ``FastMCP`` in mcp 1.x).
"""

from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path
from typing import Any, Iterator

INSTALL_HINT = "the mcp package is not installed. Install the extra: pip install 'oak-events[mcp]'"
MAX_LIMIT = 500
SCAN_DAYS = 14  # zone_state / camera_health look back at most this many daily files


def _files_newest_first(events_dir: str | Path) -> list[Path]:
    d = Path(events_dir).expanduser()
    if not d.is_dir():
        return []
    return sorted(d.glob("*.jsonl"), reverse=True)


def iter_events_newest_first(events_dir: str | Path, max_files: int | None = None) -> Iterator[dict[str, Any]]:
    """Yield events from newest to oldest. Malformed lines are skipped."""
    files = _files_newest_first(events_dir)
    if max_files is not None:
        files = files[:max_files]
    for path in files:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            if isinstance(ev, dict) and "kind" in ev:
                yield ev


def recent_events(events_dir: str | Path, limit: int = 50, kind: str | None = None) -> list[dict[str, Any]]:
    """The most recent events (oldest first within the result), optionally of one kind."""
    limit = max(1, min(int(limit), MAX_LIMIT))
    out: list[dict[str, Any]] = []
    for ev in iter_events_newest_first(events_dir):
        if kind and ev.get("kind") != kind:
            continue
        out.append(ev)
        if len(out) >= limit:
            break
    out.reverse()
    return out


def zone_state(events_dir: str | Path) -> dict[str, Any]:
    """Per zone: is a person present (from the latest person event), plus the latest depth events."""
    zones: dict[str, dict[str, Any]] = {}
    for ev in iter_events_newest_first(events_dir, max_files=SCAN_DAYS):
        kind = ev.get("kind")
        zone = ev.get("zone")
        if not zone or kind not in ("person_enter", "person_exit", "depth_change", "depth_baseline"):
            continue
        z = zones.setdefault(zone, {})
        if kind in ("person_enter", "person_exit") and "person_present" not in z:
            z["person_present"] = kind == "person_enter"
            z["person_event"] = ev
        elif kind == "depth_change" and "last_depth_change" not in z:
            z["last_depth_change"] = ev
        elif kind == "depth_baseline" and "depth_baseline" not in z:
            z["depth_baseline"] = ev
    for z in zones.values():
        z.setdefault("person_present", False)
    return {"zones": zones}


def _age_s(ts: str | None, now: _dt.datetime) -> float | None:
    if not ts:
        return None
    try:
        t = _dt.datetime.fromisoformat(ts)
    except ValueError:
        return None
    if t.tzinfo is None:
        t = t.astimezone()
    return round((now - t).total_seconds(), 1)


def camera_health(events_dir: str | Path, stale_after_s: float = 900.0,
                  now: _dt.datetime | None = None) -> dict[str, Any]:
    """Latest ``camera`` and ``alive`` events, their age, and a one-word status."""
    now = now or _dt.datetime.now().astimezone()
    last_camera = last_alive = None
    for ev in iter_events_newest_first(events_dir, max_files=SCAN_DAYS):
        if last_camera is None and ev.get("kind") == "camera":
            last_camera = ev
        elif last_alive is None and ev.get("kind") == "alive":
            last_alive = ev
        if last_camera and last_alive:
            break
    camera_age = _age_s(last_camera.get("ts") if last_camera else None, now)
    alive_age = _age_s(last_alive.get("ts") if last_alive else None, now)
    ages = [a for a in (camera_age, alive_age) if a is not None]
    newest_age = min(ages) if ages else None
    if last_camera is None and last_alive is None:
        status = "no_data"
    elif last_camera is not None and last_camera.get("state") != "up" and (
        alive_age is None or (camera_age is not None and camera_age <= alive_age)
    ):
        status = str(last_camera.get("state", "unknown"))
    elif newest_age is not None and newest_age > stale_after_s:
        status = "stale"
    else:
        status = "ok"
    return {
        "status": status,
        "last_camera": last_camera,
        "last_camera_age_s": camera_age,
        "last_alive": last_alive,
        "last_alive_age_s": alive_age,
        "stale_after_s": stale_after_s,
    }


def _server_class() -> Any:
    """FastMCP from the official SDK: ``MCPServer`` in mcp 2.x, ``FastMCP`` in mcp 1.x (same API here)."""
    try:
        from mcp.server.mcpserver import MCPServer  # noqa: PLC0415  (mcp >= 2)
        return MCPServer
    except ImportError:
        pass
    try:
        from mcp.server.fastmcp import FastMCP  # noqa: PLC0415  (mcp 1.x)
        return FastMCP
    except ImportError as exc:
        raise RuntimeError(INSTALL_HINT) from exc


def build_server(events_dir: str | Path, stale_after_s: float = 900.0) -> Any:
    """Create the MCP server with the three text-only tools."""
    server_cls = _server_class()
    events_dir = Path(events_dir).expanduser()
    server = server_cls(
        "oak-events",
        instructions=(
            "Events from an OAK camera: people entering/leaving zones and lasting depth changes. "
            "Text only; this server has no images and cannot reach the camera."
        ),
    )

    @server.tool(name="recent_events")
    def recent_events_tool(limit: int = 50, kind: str | None = None) -> str:
        """Most recent camera events as JSON (oldest first). Optional kind filter, e.g. person_enter."""
        return json.dumps(recent_events(events_dir, limit=limit, kind=kind))

    @server.tool(name="zone_state")
    def zone_state_tool() -> str:
        """Who/what is present per zone, from the latest events, as JSON."""
        return json.dumps(zone_state(events_dir))

    @server.tool(name="camera_health")
    def camera_health_tool() -> str:
        """Last camera status event and heartbeat, with their age in seconds, as JSON."""
        return json.dumps(camera_health(events_dir, stale_after_s=stale_after_s))

    return server


def serve(events_dir: str | Path, stale_after_s: float = 900.0) -> None:
    build_server(events_dir, stale_after_s=stale_after_s).run()  # stdio transport
