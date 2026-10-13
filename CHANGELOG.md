# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Configurable `oak-events mcp --stale-after SECONDS` threshold for camera health.

## [0.1.1] - 2026-10-12

### Changed

- Repository moved to [cloudlabworks/oak-events](https://github.com/cloudlabworks/oak-events);
  the MCP registry name is now `io.github.cloudlabworks/oak-events`. Old
  `issaquahd/oak-events` links redirect.
- First release published to PyPI (trusted publishing).

## [0.1.0] - 2026-10-11

### Added

- `oak-events run`: DepthAI v3 pipeline (spatial detection network + stereo
  depth) emitting JSON-line events; only detections and depth reach the host.
- Events: `person_enter`, `person_exit`, `depth_baseline`, `depth_change`,
  `camera`, `alive`.
- `PersonTracker` with confirm frames, gone timeout and confidence threshold.
- `DepthChangeDetector`: coarse depth grid with median/MAD baseline, noisy-cell
  exclusion, hold time, and pause while a person is present.
- Named zones (normalized box and/or distance range).
- JSONL sink: stdout and/or one file per local day, atomic appends, mode 0600.
- `oak-events doctor`: depthai version, devices, bootloader advice (0.0.29 for
  RVC2 PoE), privacy environment; works without depthai.
- `oak-events mcp`: MCP stdio server with `recent_events`, `zone_state` and
  `camera_health` text tools; reads event files only.
- Privacy defaults: DepthAI telemetry, crash dumps and auto-calibration off
  unless `OAK_EVENTS_ALLOW_TELEMETRY=1`.
- Device discovery by id with 90 s retry and DepthAI reconnection.
