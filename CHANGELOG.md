# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.2] - 2026-11-02

### Added

- Security and AI documentation in `docs/`: threat model, model card, data
  flow and privacy impact, SBOM (CycloneDX) with licence summary. README and
  `SECURITY.md` link them and the CloudLab Works incident response plan.
- Configurable `oak-events mcp --stale-after SECONDS` threshold for camera health.
- Atheris fuzz harness `fuzz/fuzz_events.py` for zones files and event JSONL
  files, run for 60 s on every push and pull request (`fuzz` workflow).
- `oak-events run` writes a `privacy` event before DepthAI loads, recording
  whether the DepthAI privacy defaults hold (`private`), whether telemetry
  was opted in (`telemetry_opt_in`) and which variables differ
  (`deviations`). `camera_health` returns the latest one and `private`.
- `oak-events run --model-sha256 HEX`: refuse to start (exit code 3, camera
  not opened) when the model archive's SHA-256 differs. The archive's
  SHA-256 is now recorded in every `camera` `up` event.
- `oak-events run --confidence-stats`: per-zone detection-confidence
  statistics (`n`, `mean`, `min`, `max`, `below`) in `alive` events. Off by
  default.
- `oak-events mcp --access-log FILE`: optional audit log, one JSON line per
  tool call (time, tool, argument names and value sizes, result count,
  outcome, MCP client process id). Never argument values, results or image
  content. Off by default.
- `examples/webhook.md`: alerting on privacy and model-integrity events.
- Fuzz harness also checks the access log's result count and the
  `camera_health` privacy fields.
- `docs/SHARED_RESPONSIBILITY.md` with `docs/ssrm-ownership-ai-caiq-v1.1.0.csv`:
  who owns each security control (CloudLab Works, you, the model provider),
  per CSA AI-CAIQ v1.1.0 question.
- `docs/RISK_ASSESSMENT.md`: AI risk register and AI impact assessment.
- `docs/HARDENING.md` and `examples/hardening/`: run the camera runner as a
  dedicated user under a sandboxed systemd unit and the MCP server read-only,
  without network or devices; with a container test bed.

### Changed

- Threat model: mitigations mapped to threats and a guardrail review
  procedure. Model card: verification steps, provenance, confidence
  monitoring and spot-check, bias and fairness.
- SBOM regenerated for 0.1.2 (`docs/SBOM.md`); provenance re-checked.
- README: install from PyPI.
- CI and release workflows install their tools from hash-pinned lists in
  `requirements/` (`pip install --require-hashes`), and install or build the
  package without build isolation so no unpinned package is fetched.

### Fixed

- `oak-events run --zones` now reports a malformed `z_mm` or `bbox` (not a
  list, non-numeric or boolean values) as a one-line "bad zones file" error
  naming the zone, with exit code 2, instead of a Python traceback.
- Zones files: `NaN`, `Infinity` and integers too large for a float in `z_mm`
  or `bbox` are now a "bad zones file" error. A `NaN` bound used to be
  accepted and silently matched every depth. Found by the fuzz harness.
- MCP tools: a daily event file with one invalid UTF-8 line made every tool
  fail; that line is now skipped like any other malformed line. Found by the
  fuzz harness. Lines are now split at line endings only, so a U+2028 inside a
  field (kept raw by the sink) no longer splits an event in two.
- MCP `zone_state` no longer fails on an event whose `zone` is a list or
  object, and `camera_health` no longer fails on a non-string or out-of-range
  `ts`. Found by the fuzz harness.

## [0.1.1] - 2026-10-12

### Changed

- Repository moved to [cloudlabworks/oak-events](https://github.com/cloudlabworks/oak-events);
  the MCP registry name is now `io.github.cloudlabworks/oak-events`. Old
  `issaquahd/oak-events` links redirect.
- ~~First release published to PyPI (trusted publishing).~~ Correction 2026-11-02: both release runs on 2026-10-12 failed. 0.1.1 was published to PyPI on 2026-11-02, when its release run was repeated.

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
