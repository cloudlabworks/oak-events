# oak-events

Privacy-first events from Luxonis OAK cameras for AI agents.

An OAK camera detects people, tracks them and measures depth on its own chip.
`oak-events` turns that into one JSON line per event ("a person entered the
doorway zone", "something 40 cm closer has stood in cell r2c5 for a minute")
and serves those lines to agents through an MCP server.

**Agents never receive a picture.** There is no image tool, no snapshot
command, and no code path that writes an image file.

This documentation covers oak-events 0.1.2, the current release on
[PyPI](https://pypi.org/project/oak-events/). The source is on
[GitHub](https://github.com/cloudlabworks/oak-events).

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
   default. See [Configuration](configuration.md#privacy-environment).
5. **The MCP server only reads the JSONL files.** It never opens the camera.
6. **No model download at runtime.** You point `--model` at a local NNArchive
   you fetched once.

What the events still reveal: when someone was present, for how long, how far
from the camera, and when objects moved. Treat the event files as sensitive
and keep them local.

## Where to go next

| Page | What it covers |
| --- | --- |
| [Install](install.md) | Supported hardware, installing from PyPI, fetching a model once |
| [Quickstart](quickstart.md) | Check the setup, run the camera, read events over MCP |
| [MCP server](mcp-server.md) | The three MCP tools, client configuration, access log |
| [Configuration](configuration.md) | Command line options, zones, model hash check, privacy environment |
| [Events reference](events.md) | Every event kind and its fields |
| [Running it for real](operations.md) | Supervisors, exit codes, PoE notes |
| [Security](security.md) | Reporting vulnerabilities, verifying releases, security and AI documents |
| [Contributing and licence](contributing.md) | Development setup, pull requests, MIT licence |

---

oak-events is an independent community project by CloudLab Works, not
affiliated with or endorsed by Luxonis. OAK and DepthAI are Luxonis trademarks,
used here only to say which hardware and SDK the tool works with.
