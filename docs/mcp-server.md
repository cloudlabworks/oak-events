# MCP server

`oak-events mcp --events-dir DIR` runs a stdio MCP server built on the
official `mcp` Python SDK (install the `mcp` extra). It reads the daily
`YYYY-MM-DD.jsonl` files that `oak-events run --out-dir DIR` writes.

The server never opens the camera, has no image tool, takes no path arguments
and only reads `*.jsonl` files in `DIR`. Malformed lines, including lines with
invalid UTF-8, are skipped.

## Options

| Option | Default | Meaning |
| --- | --- | --- |
| `--events-dir DIR` | required | Directory written by `oak-events run --out-dir` |
| `--stale-after SECONDS` | `900` | `camera_health` reports `stale` when the newest `camera` or `alive` event is older than this |
| `--access-log FILE` | off | Append one JSON line per tool call to `FILE` (see [Access log](#access-log)) |

## Tools

All tools return JSON text.

### `recent_events(limit=50, kind=None)`

The latest events, oldest first. `limit` is clamped to 1..500. `kind`
filters to one event kind, for example `person_enter`.

### `zone_state()`

Per zone: whether a person is present (from the latest `person_enter` or
`person_exit` event), that event, and the latest `depth_change` and
`depth_baseline` events. Looks back at most 14 daily files.

```json
{"zones": {"doorway": {"person_present": true, "person_event": {"ts": "...", "kind": "person_enter", "zone": "doorway", "count": 1, "nearest_mm": 1840}}}}
```

### `camera_health()`

The latest `camera` and `alive` events with their age in seconds, the latest
`privacy` event, and:

- `status`: `ok`, `stale` (newest event older than `--stale-after`),
  `no_data` (no `camera` or `alive` event in the last 14 daily files), or the
  last camera state (for example `not_found`, `error`) when the camera is not
  up.
- `private`: `true` or `false` from the latest `privacy` event, or `null` if
  no run has written one.

## Client configuration

Example for Claude Desktop (`examples/claude-desktop-mcp.json` in the
repository):

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

With [uv](https://docs.astral.sh/uv/) the client can run the PyPI release
without a separate install. This is the form listed in the MCP registry as
`io.github.cloudlabworks/oak-events`:

```json
{
  "mcpServers": {
    "oak-events": {
      "command": "uvx",
      "args": ["--with", "mcp", "oak-events", "mcp", "--events-dir", "/path/to/events"]
    }
  }
}
```

## Access log

`--access-log FILE` appends one JSON line per tool call to `FILE`, created
with mode 0600. Each line has `ts`, `kind` (`mcp_access`), `tool`, `args`
(each argument name with the size of its value), `result_count`, `ok`,
`error` (exception type) when a call failed, and `client_pid` (the process
that started the server, normally the MCP client).

Argument values and results are never written: the log shows that an agent
read events, not what it read. `FILE` must be outside the events directory,
otherwise the tools would serve it as events.

## Running the server isolated

The [hardening guide](HARDENING.md) runs the MCP server read-only, with no
network and no devices, under a dedicated user.
