# oak-events

Privacy-first events from Luxonis OAK cameras for AI agents.

An OAK camera detects people, tracks them and measures depth on its own chip.
`oak-events` turns that into one JSON line per event ("a person entered the
doorway zone", "something 40 cm closer has stood in cell r2c5 for a minute")
and serves those lines to agents through an MCP server.

**Agents never receive a picture.** There is no image tool, no snapshot
command, and no code path that writes an image file.

## Why

Giving an agent a camera usually means giving it a video feed. Most agent
questions do not need one: *is anyone at the bench? did something on the shelf
move? is the camera alive?* Those are answerable from detections and a coarse
depth grid, which carry far less about the people in view than frames do.

## Privacy model

Stated plainly, so you can check it against the code:

1. **Colour frames stay on the camera.** The colour sensor feeds the on-chip
   detection network. Its frames are never linked to a host output queue.
   Only two streams reach the host: detection results (label, confidence,
   3-D position, normalized box) and the stereo depth map
   (`src/oak_events/camera.py`).
2. **Depth maps are reduced and dropped.** Each depth frame becomes a grid of
   cell medians (default 6 x 8) in memory, then is discarded. No depth map is
   stored.
3. **Only JSON lines are written**, to stdout and/or a daily `.jsonl` file.
   A test scans the repo and a temporary run directory for image files.
4. **DepthAI telemetry, crash-dump upload and auto-calibration are off** by
   default. `oak_events.privacy` forces `DEPTHAI_TELEMETRY=0`,
   `DEPTHAI_DISABLE_CRASHDUMP_COLLECTION=1` and `DEPTHAI_AUTOCALIBRATION=OFF`
   before `depthai` is imported. Only `OAK_EVENTS_ALLOW_TELEMETRY=1` leaves
   DepthAI's own defaults in place.
5. **The MCP server only reads the JSONL files.** It never opens the camera.
6. **No model download at runtime.** You point `--model` at a local NNArchive
   you fetched once.

What the events still reveal: when someone was present, for how long, how far
from the camera, and when objects moved. Treat the event files as sensitive
and keep them local.

## Supported hardware

| Device | Status |
| --- | --- |
| RVC2: OAK-D PoE | Tested live (DepthAI 3.11, bootloader 0.0.29, macOS arm64) |
| RVC2: OAK-D (USB) | Expected to work; untested, reports welcome |
| RVC4 (e.g. OAK 4) | Untested; reports welcome |

Requires DepthAI v3 (`depthai>=3.9`) and Python 3.10+.

## Quickstart

```bash
# Not on PyPI yet: install the v0.1.0 release from GitHub
pip install 'oak-events[camera,mcp] @ git+https://github.com/cloudlabworks/oak-events@v0.1.0'

# 1. Check the setup (works without a camera or depthai installed)
oak-events doctor

# 2. Fetch a detection model ONCE (see below), then run
oak-events run --model ~/models/yolov6-nano.rvc2.tar.xz --out-dir ~/.local/share/oak-events/events

# 3. Let an agent read the events over MCP
oak-events mcp --events-dir ~/.local/share/oak-events/events
```

### Fetching a model once

`oak-events` never downloads at runtime. Fetch an NNArchive from the Luxonis
model zoo once, with DepthAI itself, and keep the file:

```python
import depthai as dai

path = dai.getModelFromZoo(
    dai.NNModelDescription(model="luxonis/yolov6-nano:r2-coco-512x288", platform="RVC2")
)
print(path)  # copy this .tar.xz somewhere stable and pass it to --model
```

This one step contacts the Luxonis model hub. Check the exact model slug on the
Luxonis model zoo; any detection NNArchive whose classes include `person`
works (use `--person-label` if the class has another name). For RVC4, use
`platform="RVC4"`.

### Zones

By default everything is reported for one zone named `view`. A zones file
names regions by normalized image box and/or distance:

```json
{"zones": [
  {"name": "doorway", "bbox": [0.0, 0.0, 0.35, 1.0]},
  {"name": "desk", "bbox": [0.4, 0.3, 1.0, 1.0], "z_mm": [400, 2500]}
]}
```

`bbox` is `[x0, y0, x1, y1]` in 0..1 with the origin top-left; `z_mm` is
`[min, max]` distance in millimetres (either side may be `null`). Each zone
gets its own person tracker and depth-change grid. The depth map is aligned to
the colour camera only approximately, so leave some margin.

## Commands

| Command | What it does |
| --- | --- |
| `oak-events run --model PATH [--device-id ID] [--out-dir DIR] [--zones FILE] [--fps 10]` | Run the camera; print events, optionally append to `DIR/YYYY-MM-DD.jsonl` |
| `oak-events doctor [--json]` | depthai version, visible devices, bootloader advice, privacy env state |
| `oak-events mcp --events-dir DIR` | MCP stdio server with `recent_events`, `zone_state`, `camera_health` |

## Event schema

Every line is a JSON object with `ts` (ISO-8601 local time with offset),
`kind`, and the fields below.

| kind | fields | meaning |
| --- | --- | --- |
| `person_enter` | `zone`, `count`, `nearest_mm` | a person was seen in `confirm_frames` (3) consecutive frames |
| `person_exit` | `zone`, `dwell_s` | nobody seen for `gone_seconds` (10); dwell = first to last sighting |
| `depth_baseline` | `zone`, `cells_judged`, `cells_noisy`, `grid` | baseline built; noisy cells (stereo noise, low texture) are ignored |
| `depth_change` | `zone`, `cells` (e.g. `["r0c3"]`), `delta_mm` | a cell's depth moved > 15 % for `--hold-seconds` (60) with nobody present |
| `camera` | `state` (`up`, `not_found`, `error`, `reconnect`, `pipeline_stopped`, `stopped`), plus `device`, `device_model`, `bootloader`, `model`, `detail` as relevant | camera lifecycle |
| `alive` | `det_fps`, `person`, `occupied` | heartbeat every `--alive-every` seconds (300) |

Example:

```json
{"ts": "2026-10-11T09:14:03-07:00", "kind": "person_enter", "zone": "doorway", "count": 1, "nearest_mm": 1840}
```

Depth-change detection pauses while a person is present in that zone: people
are not scenery.

## MCP

`oak-events mcp --events-dir DIR` runs a stdio MCP server (official `mcp`
Python SDK). Tools, all returning JSON text:

- `recent_events(limit=50, kind=None)` - latest events, oldest first
- `zone_state()` - per zone: person present or not, latest person and depth events
- `camera_health()` - latest `camera` and `alive` events with their age and a status (`ok`, `stale`, `no_data`, or the last camera state)

See `examples/claude-desktop-mcp.json` for a client config, and
`examples/openclaw-stream.md` / `examples/webhook.md` for wiring the event
stream into automations.

## Running it for real

Run `oak-events run` under a supervisor that restarts it on exit (systemd,
launchd, a container restart policy). The process exits with a `camera` event
explaining why: `not_found`, `error`, `pipeline_stopped`.

### PoE notes

- **Bootloader:** RVC2 PoE devices with a bootloader older than **0.0.29** can
  fail discovery; 0.0.29 fixes it. `oak-events doctor` shows the version when
  the device is not in use.
- **The device can take from ~30 s to a few minutes to free up** after a
  previous host disconnects (2.5 min observed on an OAK-D PoE). `oak-events
  run` retries discovery for up to 4 minutes (240 s), then asks DepthAI to
  reconnect up to 5 times before giving up.
- **macOS launchd:** observed, cause not proven: under a launchd job the device
  could fail with `X_LINK_DEVICE_NOT_FOUND` while the same command worked from
  a terminal. Running it under a supervisor process that has macOS
  local-network permission worked. If you see this, check
  *System Settings > Privacy & Security > Local Network*.
- Prefer `--device-id` over addresses; the id survives network changes.

## Development

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[mcp]' pytest
.venv/bin/pytest -q
```

Tests need neither a camera nor `depthai`. See `CONTRIBUTING.md`.

## License

MIT. See `LICENSE`.

---

oak-events is an independent community project, not affiliated with or endorsed by Luxonis. OAK and DepthAI are Luxonis trademarks, used here only to say which hardware and SDK the tool works with.

<!-- mcp-name: io.github.cloudlabworks/oak-events -->
