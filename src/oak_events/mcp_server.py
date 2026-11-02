"""MCP stdio server: text-only tools over the JSONL event files.

The server reads the files written by ``oak-events run --out-dir DIR``. It
never opens the camera and has no way to return a picture: every tool returns
JSON text built from event lines.

The tool logic lives in plain functions (``recent_events``, ``zone_state``,
``camera_health``) so it can be used and tested without the ``mcp`` package;
``build_server`` wraps them with FastMCP from the official MCP Python SDK
(``MCPServer`` in mcp 2.x, ``FastMCP`` in mcp 1.x).

With ``--access-log FILE`` every tool call is recorded in ``FILE`` (see
``AccessLog``). It is off by default.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
from pathlib import Path
from typing import Any, Callable, Iterator

from .events import make_event

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
            data = path.read_bytes()
        except OSError:
            continue
        # Split bytes, not text: str.splitlines() also breaks at U+2028 and other
        # separators that json.dumps(ensure_ascii=False) leaves inside a line.
        # Decoding per line skips a line with bad UTF-8 instead of the whole file.
        for raw in reversed(data.splitlines()):
            try:
                line = raw.decode("utf-8").strip()
            except UnicodeDecodeError:
                continue
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
        if not isinstance(zone, str) or not zone or kind not in ("person_enter", "person_exit", "depth_change", "depth_baseline"):
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
    if not isinstance(ts, str) or not ts:
        return None
    try:
        t = _dt.datetime.fromisoformat(ts)
        if t.tzinfo is None:
            t = t.astimezone()
        return round((now - t).total_seconds(), 1)
    except (ValueError, OverflowError):  # not ISO-8601, or too close to year 1 / 9999 to shift
        return None


def camera_health(events_dir: str | Path, stale_after_s: float = 900.0,
                  now: _dt.datetime | None = None) -> dict[str, Any]:
    """Latest ``camera`` and ``alive`` events, their age, and a one-word status.

    Also the latest ``privacy`` event and ``private``: ``True`` or ``False``
    from that event, ``None`` when there is none (older versions do not write it).
    """
    now = now or _dt.datetime.now().astimezone()
    last_camera = last_alive = last_privacy = None
    for ev in iter_events_newest_first(events_dir, max_files=SCAN_DAYS):
        kind = ev.get("kind")
        if last_camera is None and kind == "camera":
            last_camera = ev
        elif last_alive is None and kind == "alive":
            last_alive = ev
        elif last_privacy is None and kind == "privacy":
            last_privacy = ev
        if last_camera and last_alive and last_privacy:
            break
    private = last_privacy.get("private") if last_privacy else None
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
        "last_privacy": last_privacy,
        "private": private if isinstance(private, bool) else None,
    }


# --------------------------------------------------------------------------- access log


def _value_size(value: Any) -> int:
    """Size of an argument value: characters for text, JSON length otherwise, 0 for None."""
    if value is None:
        return 0
    if isinstance(value, str):
        return len(value)
    return len(json.dumps(value, default=str))


def result_count(tool: str, result: Any) -> int:
    """How many items a tool returned: events, zones, or (for camera_health) events found."""
    if tool == "recent_events" and isinstance(result, list):
        return len(result)
    if tool == "zone_state" and isinstance(result, dict):
        return len(result.get("zones") or {})
    if tool == "camera_health" and isinstance(result, dict):
        return sum(result.get(k) is not None for k in ("last_camera", "last_alive", "last_privacy"))
    return 0


def check_access_log_path(events_dir: str | Path, path: str | Path) -> Path:
    """The access log must not live in the events directory, or the tools would serve it as events."""
    log = Path(path).expanduser().resolve()
    if log.parent == Path(events_dir).expanduser().resolve():
        raise ValueError("the access log must be outside the events directory")
    if log.is_dir():
        raise ValueError(f"access log path is a directory: {log.name}")
    return log


class AccessLog:
    """Audit record of MCP tool calls, one JSON line per call, file mode 0600.

    Each line has ``ts``, ``kind`` ``mcp_access``, ``tool``, ``args`` (each
    argument name with the size of its value), ``result_count``, ``ok``,
    ``error`` (exception type) when a call failed, and ``client_pid`` (the
    process that started this stdio server, normally the MCP client).
    Argument values and results are never written: the log shows that an
    agent read events, not what it read. The server has no image content.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, tool: str, args: dict[str, Any], count: int | None, error: str | None = None) -> dict[str, Any]:
        fields: dict[str, Any] = {
            "tool": tool,
            "args": {key: _value_size(value) for key, value in sorted(args.items())},
            "result_count": count,
            "ok": error is None,
            "client_pid": os.getppid(),
        }
        if error is not None:
            fields["error"] = error
        entry = make_event("mcp_access", **fields)
        data = (json.dumps(entry, ensure_ascii=False) + "\n").encode("utf-8")
        fd = os.open(self.path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        try:
            written = os.write(fd, data)
            while written < len(data):
                written += os.write(fd, data[written:])
        finally:
            os.close(fd)
        return entry


def call_tool(tool: str, fn: Callable[[], Any], args: dict[str, Any], access_log: AccessLog | None = None) -> str:
    """Run one tool, record it in the access log if there is one, and return its JSON text."""
    try:
        result = fn()
    except Exception as exc:
        if access_log is not None:
            access_log.record(tool, args, None, error=type(exc).__name__)
        raise
    if access_log is not None:
        access_log.record(tool, args, result_count(tool, result))
    return json.dumps(result)


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


def build_server(events_dir: str | Path, stale_after_s: float = 900.0, access_log: str | Path | None = None) -> Any:
    """Create the MCP server with the three text-only tools."""
    server_cls = _server_class()
    events_dir = Path(events_dir).expanduser()
    log = AccessLog(check_access_log_path(events_dir, access_log)) if access_log is not None else None
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
        return call_tool("recent_events", lambda: recent_events(events_dir, limit=limit, kind=kind),
                         {"limit": limit, "kind": kind}, log)

    @server.tool(name="zone_state")
    def zone_state_tool() -> str:
        """Who/what is present per zone, from the latest events, as JSON."""
        return call_tool("zone_state", lambda: zone_state(events_dir), {}, log)

    @server.tool(name="camera_health")
    def camera_health_tool() -> str:
        """Last camera status event and heartbeat, with their age in seconds, as JSON."""
        return call_tool("camera_health", lambda: camera_health(events_dir, stale_after_s=stale_after_s), {}, log)

    return server


def serve(events_dir: str | Path, stale_after_s: float = 900.0, access_log: str | Path | None = None) -> None:
    build_server(events_dir, stale_after_s=stale_after_s, access_log=access_log).run()  # stdio transport
