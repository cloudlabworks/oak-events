# Configuration

oak-events has no configuration file. Everything is a command line option, a
zones file, or an environment variable.

## `oak-events run`

| Option | Default | Meaning |
| --- | --- | --- |
| `--model PATH` | required | Local detection NNArchive (`.tar.xz`), fetched once (see [Install](install.md#fetch-a-model-once)) |
| `--device-id ID` | first device found | Device to open. Prefer it over addresses; the id survives network changes |
| `--out-dir DIR` | none | Also append events to `DIR/YYYY-MM-DD.jsonl` (mode 0600) |
| `--zones FILE` | one zone, `view` | Zones file (see [Zones](#zones)) |
| `--fps N` | `10` | Detection frame rate |
| `--alive-every SECONDS` | `300` | Interval of the `alive` heartbeat event |
| `--person-label NAME` | `person` | Model class treated as a person |
| `--person-confidence X` | `0.5` | Minimum detection confidence for a person |
| `--hold-seconds SECONDS` | `60` | How long a depth change must persist before it is reported |
| `--model-sha256 HEX` | off | Refuse to start unless the model archive has this SHA-256 |
| `--confidence-stats` | off | Add per-zone detection-confidence statistics to `alive` events |
| `--quiet` | off | Do not echo events to stdout |

For `oak-events mcp` options, see [MCP server](mcp-server.md#options).
`oak-events doctor` takes only `--json`.

## Zones

By default everything is reported for one zone named `view`: the whole field
of view at any distance. A zones file names regions by normalized image box
and/or distance:

```json
{
  "zones": [
    {"name": "doorway", "bbox": [0.0, 0.0, 0.35, 1.0]},
    {"name": "desk", "bbox": [0.4, 0.3, 1.0, 1.0], "z_mm": [400, 2500]},
    {"name": "far_wall", "z_mm": [3000, null]}
  ]
}
```

- `bbox` is `[x0, y0, x1, y1]` in 0..1 with the origin top-left, and must
  satisfy `0 <= x0 < x1 <= 1` and `0 <= y0 < y1 <= 1`.
- `z_mm` is `[min, max]` distance from the camera in millimetres. Either side
  may be `null`; if both are set, `min` must be below `max`.
- A zone may have `bbox`, `z_mm`, both, or neither.
- Numbers must be finite: `NaN` and `Infinity` are rejected.

Each zone gets its own person tracker and depth-change grid. The depth map is
aligned to the colour camera only approximately, so leave some margin.

A malformed file stops `oak-events run` with a one-line `bad zones file` error
naming the zone, and exit code 2.

## Model integrity check

The SHA-256 of the model archive is computed at every start and recorded in
the `camera` `up` event (`model_sha256`), with or without any option.

`--model-sha256 HEX` compares that hash with `HEX` (64 hexadecimal
characters) before the camera is opened. On a mismatch oak-events writes a
`camera` event with state `error`, `model_sha256` and `expected_sha256`, and
exits with code 3. The reference hash of the tested archive is in the
[model card](MODEL_CARD.md).

## Confidence statistics

`--confidence-stats` adds a `confidence` object to each `alive` event: per
zone, `n` counts per-frame person detections at or above
`--person-confidence`, `below` counts those under it, and `mean`, `min` and
`max` describe the accepted ones (`null` when `n` is 0). Each `alive` event
covers the time since the previous one. On a scene that does not change, a
falling mean or a rising `below` count means the model, the camera or the
light changed. The [model card](MODEL_CARD.md) describes a spot-check
procedure.

## Privacy environment

Before `depthai` is imported, oak-events forces these variables, overwriting
any value already set:

| Variable | Forced value | Effect |
| --- | --- | --- |
| `DEPTHAI_TELEMETRY` | `0` | DepthAI telemetry off |
| `DEPTHAI_DISABLE_CRASHDUMP_COLLECTION` | `1` | Crash-dump upload off |
| `DEPTHAI_AUTOCALIBRATION` | `OFF` | On-device auto-calibration off |

The only way to keep DepthAI's own defaults is `OAK_EVENTS_ALLOW_TELEMETRY=1`,
in which case oak-events leaves the environment untouched.

Every run writes a `privacy` event before DepthAI loads: `private` is `false`
if any of the three variables differs from the private value, and
`deviations` names them. `oak-events doctor` shows the same state, and the MCP
`camera_health` tool returns the latest `privacy` event.
