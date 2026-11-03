# Events reference

Every event is one JSON object on one line, with `ts` (ISO-8601 local time
with offset, to the second), `kind`, and the fields below. `oak-events run`
prints events to stdout and, with `--out-dir DIR`, appends them to
`DIR/YYYY-MM-DD.jsonl`.

```json
{"ts": "2026-10-11T09:14:03-07:00", "kind": "person_enter", "zone": "doorway", "count": 1, "nearest_mm": 1840}
```

## Event kinds

| kind | fields | meaning |
| --- | --- | --- |
| `person_enter` | `zone`, `count`, `nearest_mm` | A person was seen in 3 consecutive frames |
| `person_exit` | `zone`, `dwell_s` | Nobody seen for 10 seconds; dwell is first to last sighting |
| `depth_baseline` | `zone`, `cells_judged`, `cells_noisy`, `grid` | Baseline built; noisy cells (stereo noise, low texture) are ignored |
| `depth_change` | `zone`, `cells` (for example `["r0c3"]`), `delta_mm` | A cell's depth moved more than 15 % for `--hold-seconds` (60) with nobody present |
| `camera` | `state`, plus the fields below as relevant | Camera lifecycle |
| `alive` | `det_fps`, `person`, `occupied`; with `--confidence-stats` also `confidence` | Heartbeat every `--alive-every` seconds (300) |
| `privacy` | `private`, `telemetry_opt_in`, `deviations` | Written once per run, before DepthAI loads |

## People

A person tracker runs per zone. A detection counts when its label is
`--person-label` (`person`), its confidence is at least `--person-confidence`
(0.5), and it falls inside the zone.

- `person_enter` fires after 3 consecutive frames with a person. `count` is
  the number of people in that frame, `nearest_mm` the distance of the
  nearest one.
- `person_exit` fires once nobody has been seen for 10 seconds. `dwell_s` is
  the time from first to last sighting, in whole seconds.

## Depth

Each depth frame is reduced to a grid of cell medians (default 6 rows by 8
columns) per zone and then dropped. Cells are named `r<row>c<column>`,
starting at `r0c0` top-left.

- `depth_baseline`: the first 60 depth frames build a baseline. `grid` is
  `[rows, columns]`, `cells_judged` the cells that will be watched, and
  `cells_noisy` the cells ignored because their depth is unstable or often
  invalid.
- `depth_change`: one or more cells differ from the baseline by more than
  15 % for `--hold-seconds`. `cells` lists them and `delta_mm` gives the
  signed change for each, in the same order (negative means closer). The
  baseline of those cells then moves to the new depth.

Depth-change detection pauses while a person is present in that zone: people
are not scenery.

## Camera lifecycle

`camera` events carry `state`:

| state | When | Extra fields |
| --- | --- | --- |
| `up` | Pipeline started | `device`, `device_model`, `bootloader`, `model`, `model_sha256`, `model_sha256_checked`, `zones` |
| `not_found` | No device found after up to 240 seconds of discovery | `device` |
| `reconnect` | DepthAI is reconnecting (up to 5 attempts) | `detail` |
| `pipeline_stopped` | The pipeline stopped running | |
| `error` | Model archive missing, model hash mismatch, or an unexpected error | `detail`; on a hash mismatch also `model`, `model_sha256`, `expected_sha256` |
| `stopped` | Stopped with Ctrl+C | |

For the exit code that goes with each state, see
[Running it for real](operations.md#exit-codes).

## Heartbeat

`alive` events report `det_fps` (detection frames per second since the
previous heartbeat), `person` (`true` if any zone has a person present) and
`occupied` (the zones with a person present).

With `--confidence-stats`, `confidence` holds per zone `n`, `mean`, `min`,
`max` and `below`; see
[Configuration](configuration.md#confidence-statistics).

## Privacy

The `privacy` event records whether the DepthAI privacy defaults held for this
run: `private` is `false` if any DepthAI privacy variable differs from the
private value, `telemetry_opt_in` is `true` if `OAK_EVENTS_ALLOW_TELEMETRY=1`
was set, and `deviations` names the variables that differ. See
[Configuration](configuration.md#privacy-environment).

## What events never contain

No event carries image data, a depth map, or an array of pixels. The only
spatial data is the per-zone grid size, cell names, distances in millimetres
and normalized zone boxes from your zones file.
