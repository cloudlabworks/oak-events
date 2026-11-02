# oak-events data flow, retention and privacy impact

| | |
| --- | --- |
| Owner | Alex Alvord, CloudLab Works |
| Version | Published 2026-11-02; written against commit 00d9053 |
| Review | At least once a year (next by 2027-11-01) and whenever an event field, output or default changes |

## 1. Who owns the data

The person or organization that runs oak-events (the deployer) owns and controls all data it produces.
**CloudLab Works receives none of it:** oak-events has no telemetry, no update check, no account and no
hosted service. The deployer is the data controller under privacy law; CloudLab Works is not a processor.

## 2. What flows where

| Step | Data | Where it goes | Kept? |
| --- | --- | --- | --- |
| 1 | Colour frames | Colour sensor to the detector on the camera chip | **Never leave the camera.** No host queue exists for them |
| 2 | Stereo depth map (640 x 400) | Camera to host memory | Reduced at once to a grid of cell medians (default 6 x 8), then dropped. Never written |
| 3 | Detections (label, confidence, 3-D position, box centre) | Camera to host memory | Turned into events, then dropped |
| 4 | Events (JSON lines) | stdout, and with `--out-dir` the file `DIR/YYYY-MM-DD.jsonl`, mode 0600 | **Yes, on the deployer's host** |
| 5 | Events | `oak-events mcp` reads the files and returns JSON text to the MCP client over stdio | Not stored by oak-events |
| 6 | Events | The MCP client (an AI agent) may send them to its model provider | Outside oak-events; the deployer chooses the agent and provider |

oak-events itself opens no internet connections (on PoE it talks to the camera over the local network). DepthAI telemetry, crash-dump upload and auto-calibration are
forced off unless the deployer sets `OAK_EVENTS_ALLOW_TELEMETRY=1`. Fetching the model archive once, before
first use, contacts the Luxonis model hub; that is done by the deployer with DepthAI, not by oak-events.

For PoE cameras, the camera-to-host link is ordinary local network traffic with no authentication or
encryption added by oak-events. Keep the camera on an isolated network segment that only the oak-events host
can reach.

## 3. What is stored

Event fields (full schema in the README):

| Kind | Fields | Sensitivity |
| --- | --- | --- |
| `person_enter`, `person_exit` | time, zone, count, nearest distance, dwell seconds | Personal data in most homes and small workplaces |
| `depth_baseline`, `depth_change` | time, zone, grid cells, depth change | Low; can show when objects moved |
| `alive` | time, frame rate, whether anyone is present, occupied zones | Personal data (presence) |
| `camera` | time, state, device id, device model, bootloader version, model file name, error detail | Device id identifies the camera; error detail may contain local file paths |

**Not stored:** pictures, depth maps, face or body features, embeddings, audio (no microphone is used),
names or identities.

**Other copies the deployer may create:** if oak-events runs under a supervisor without `--quiet`, the
supervisor's log (for example the systemd journal) also keeps every event. Agents and their model providers
may keep what they receive.

## 4. Retention and deletion

**oak-events never deletes event files today.** It appends to one file per local day indefinitely. The MCP
server looks back at most 14 daily files for `zone_state` and `camera_health`; `recent_events` can read
every file. Nothing rotates, archives or deletes them.

Deployers must set a retention period. Example, keep 30 days (run daily from cron, a systemd timer or
launchd):

```bash
find "$EVENTS_DIR" -name '*.jsonl' -type f -mtime +30 -delete
```

Deleting the files deletes everything oak-events stored. Also clear supervisor logs if they hold events.
**Commitment:** an optional `--retain-days` setting in `oak-events run` by 2027-03-31.

## 5. Redacting before sharing

Remove the camera id, device details and error text, and coarsen time to the hour, before attaching events to
an issue or sharing them:

```bash
jq -c 'del(.device, .device_model, .bootloader, .detail) | .ts |= (.[0:13] + ":00:00" + .[19:])' DIR/2026-11-02.jsonl
```

## 6. Portability

Events are UTF-8 JSON lines with a documented schema; any tool can read them. Export is a file copy. There
is no proprietary format, account or lock-in, and the code is MIT licensed.

## 7. Privacy impact summary

Prepared to help deployers with their own assessment. It is not a substitute for a DPIA where law requires
one (for example systematic monitoring under GDPR Article 35).

| Question | Assessment |
| --- | --- |
| Origin | A camera the deployer installs in their own space |
| Nature | Presence, count, distance and dwell time of people in named zones; when objects moved. No images or identities |
| Particularity | In a home or small office the few people present are known, so presence events show their routines: when they are home, asleep, away or together. Long retention builds a detailed pattern of life |
| Severity if disclosed | Medium to high: reveals absence (burglary risk) and personal routines. Low if files stay on the host, are owner-only and are kept for a short time |
| Built-in mitigations | No pictures leave the camera; depth maps dropped; files mode 0600; no telemetry; read-only MCP tools |
| Deployer actions | Tell people a camera is in use; keep the event directory private; set retention (section 4); redact before sharing (section 5); choose an agent and model provider whose data terms you accept; keep a human in control of actions; run a DPIA if your law requires it |
