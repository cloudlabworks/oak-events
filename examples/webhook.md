# Piping events to a webhook

Every event is one JSON line, so a shell loop is enough to forward them.

```bash
oak-events run --model ~/models/yolov6-nano.rvc2.tar.xz \
  | grep --line-buffered -E '"kind": "(person_enter|person_exit|camera)"' \
  | while IFS= read -r line; do
      curl -sS -X POST -H 'Content-Type: application/json' \
        --data-binary "$line" "$WEBHOOK_URL" > /dev/null
    done
```

- Set `WEBHOOK_URL` to your endpoint (Home Assistant, n8n, a chat webhook...).
  Prefer HTTPS; event lines say when people were present.
- `grep --line-buffered` matters: without it events are held in a buffer.
- Need a different payload shape? Reshape each line with `jq`, e.g.
  `jq -c '{text: "\(.kind) in \(.zone // "camera")"}'`.

Following the daily files instead of stdout (for example from another host
user) works the same way:

```bash
tail -F ~/.local/share/oak-events/events/"$(date +%F)".jsonl | ...
```

Note that `tail -F` on a dated file does not roll over at midnight; restart it
daily or read stdout instead.

## Alerting on security events

Two events mean something security-relevant changed. Forward them to a place
a person reads:

- `privacy` with `"private": false`: DepthAI telemetry, crash-dump upload or
  auto-calibration is not in its private default for this run (`deviations`
  says which).
- `camera` with `"state": "error"` and a `detail` starting `model archive
  SHA-256 mismatch`: the model file is not the one you pinned with
  `--model-sha256`.

```bash
oak-events run --model ~/models/yolov6-nano.rvc2.tar.xz --model-sha256 "$MODEL_SHA256" \
  | jq -c --unbuffered 'select((.kind == "privacy" and .private != true)
                              or (.kind == "camera" and .state == "error"))' \
  | while IFS= read -r line; do
      curl -sS -X POST -H 'Content-Type: application/json' \
        --data-binary "$line" "$ALERT_WEBHOOK_URL" > /dev/null
    done
```

An agent can check the same thing through MCP: `camera_health` returns
`"private": false` after such a run. If you run `oak-events mcp --access-log
FILE`, `FILE` is a record of which tool calls the agent made; keep it with
your other logs.
