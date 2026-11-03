# Quickstart

This takes you from a fresh install to an agent reading camera events. It
assumes you installed `oak-events[camera,mcp]` and fetched a model archive
once (see [Install](install.md)).

## 1. Check the setup

```bash
oak-events doctor
```

`doctor` prints the oak-events, Python, DepthAI and MCP SDK versions, the
DepthAI privacy settings, and every visible device with its bootloader version
and advice. Add `--json` for machine-readable output.

If no device is listed, see the [PoE notes](operations.md#poe-notes): a PoE
camera can take from about 30 seconds to a few minutes to free up after
another host disconnects, and on macOS the process needs local-network
permission.

## 2. Run the camera

```bash
oak-events run \
  --model ~/models/yolov6-nano.rvc2.tar.xz \
  --out-dir ~/.local/share/oak-events/events
```

Events print to stdout, one JSON object per line, and are appended to
`~/.local/share/oak-events/events/YYYY-MM-DD.jsonl` (files are created with
mode 0600). The first lines are a `privacy` event, written before DepthAI
loads, and a `camera` event with state `up`:

```json
{"ts": "2026-10-11T09:14:03-07:00", "kind": "person_enter", "zone": "doorway", "count": 1, "nearest_mm": 1840}
```

Without a zones file everything is reported for one zone named `view`. To name
regions such as a doorway or a desk, see
[Zones](configuration.md#zones). Every event kind is listed in the
[Events reference](events.md).

Stop with Ctrl+C; oak-events writes a `camera` event with state `stopped`.

## 3. Let an agent read the events

```bash
oak-events mcp --events-dir ~/.local/share/oak-events/events
```

This starts a stdio MCP server with three read-only tools: `recent_events`,
`zone_state` and `camera_health`. Normally your MCP client starts it for you.
For example, a Claude Desktop configuration:

```json
{
  "mcpServers": {
    "oak-events": {
      "command": "oak-events",
      "args": ["mcp", "--events-dir", "~/.local/share/oak-events/events"]
    }
  }
}
```

See [MCP server](mcp-server.md) for the tools and their output.

## Next steps

- Keep the camera runner alive under a supervisor: [Running it for real](operations.md).
- Isolate the runner and the MCP server: the
  [hardening guide](HARDENING.md) runs both under a dedicated user, with a
  read-only, network-free MCP server.
- Wire the event stream into automations: see
  [`examples/openclaw-stream.md`](https://github.com/cloudlabworks/oak-events/blob/main/examples/openclaw-stream.md)
  and [`examples/webhook.md`](https://github.com/cloudlabworks/oak-events/blob/main/examples/webhook.md).
