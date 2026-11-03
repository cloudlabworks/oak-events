# Running it for real

Run `oak-events run` under a supervisor that restarts it on exit (systemd,
launchd, a container restart policy). The process does not restart itself:
it exits with a `camera` event explaining why.

## Exit codes

| Code | Last `camera` state | Cause |
| --- | --- | --- |
| `0` | `stopped` | Interrupted (Ctrl+C) |
| `1` | `pipeline_stopped` or `error` | The pipeline stopped, or an unexpected error (`detail` says which) |
| `2` | `not_found`, or none | No device found after discovery, or a bad zones file (one-line error on stderr) |
| `3` | `error` | Model archive not found, or its SHA-256 does not match `--model-sha256`; the camera was not opened |
| `4` | none | `depthai` is not installed (install the `camera` extra) |

`oak-events mcp` exits with code 2 for a bad `--access-log` path and 4 when
the `mcp` package is not installed.

## Monitoring

The MCP `camera_health` tool (see [MCP server](mcp-server.md#camera_health))
gives a one-word status from the latest `camera` and `alive` events. Outside
an agent, watch the events directory for `camera` events other than `up`, an
`alive` gap longer than `--alive-every`, or a `privacy` event with `private`
set to `false`. `examples/webhook.md` in the repository shows alerting on the
privacy and model-integrity events.

## Isolation

The [hardening guide](HARDENING.md) runs the camera runner as a dedicated
user under a sandboxed systemd unit and the MCP server read-only, without
network or devices, with a container test bed.

## PoE notes

- **Bootloader:** RVC2 PoE devices with a bootloader older than **0.0.29** can
  fail discovery; 0.0.29 fixes it. `oak-events doctor` shows the version when
  the device is not in use.
- **The device can take from about 30 seconds to a few minutes to free up**
  after a previous host disconnects (2.5 minutes observed on an OAK-D PoE).
  `oak-events run` retries discovery for up to 4 minutes (240 seconds), then
  asks DepthAI to reconnect up to 5 times before giving up.
- **macOS launchd:** observed, cause not proven: under a launchd job the device
  could fail with `X_LINK_DEVICE_NOT_FOUND` while the same command worked from
  a terminal. Running it under a supervisor process that has macOS
  local-network permission worked. If you see this, check
  *System Settings > Privacy & Security > Local Network*.
- Prefer `--device-id` over addresses; the id survives network changes.
