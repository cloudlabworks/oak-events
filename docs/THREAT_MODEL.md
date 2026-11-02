# oak-events threat model

| | |
| --- | --- |
| Owner | Alex Alvord, CloudLab Works |
| Version | Published 2026-11-02; written against commit 00d9053 (oak-events 0.1.1 plus unreleased changes) |
| Review | At least once a year (next by 2027-11-01) and whenever the event schema, MCP tools, host output queues, privacy defaults or reference model change |
| Method | STRIDE per trust boundary; MITRE ATLAS for threats to the model; OWASP Top 10 for LLM Applications (2025) for the agent boundary |

## 1. System

```
 [OAK camera]                 [host: oak-events run]            [events dir]          [oak-events mcp]        [MCP client / agent]
 colour sensor -> on-chip     detections + depth map    write   DIR/YYYY-MM-DD.jsonl   read  JSON text tools    stdio   LLM agent
 detector + stereo depth  ==B1==> trackers, cell medians ==B2==> (mode 0600)       ==B3==> recent_events,  ==B4==> (customer's choice)
                                                                                        zone_state, camera_health
 Supply chain (B5): PyPI dependencies, DepthAI wheel and device firmware, model archive (Luxonis zoo), GitHub Actions
```

**Assets, in priority order:** privacy of the people in view; integrity of the events agents act on;
integrity of oak-events releases; availability of the event stream.

**Trust boundaries**

- **B1 camera to host.** USB or Ethernet (PoE) link run by DepthAI. Only two streams cross it: detections
  and the stereo depth map. oak-events adds no authentication or encryption on this link.
- **B2 host process to disk.** Only JSON lines are written, to stdout and/or daily files with mode 0600.
- **B3 events directory to MCP server.** The server reads `*.jsonl` files in one directory, never the camera.
- **B4 MCP server to agent.** Three read-only tools return JSON text. The agent and its model provider are
  outside oak-events' control; any events the agent receives may be sent to that provider.
- **B5 supply chain.** Code and binaries oak-events depends on.

## 2. Threats and mitigations

Risk is likelihood times impact, each Low, Medium or High. The residual column is the risk after current
mitigations.

| ID | Threat | Framework | Current mitigations | Residual |
| --- | --- | --- | --- | --- |
| T1 | A code change links colour or preview frames to a host queue or writes images or depth maps to disk | STRIDE I | Only two host queues, with a code comment forbidding more (`camera.py`); `tests/test_no_images.py`; `CONTRIBUTING.md` rule; pull request review; CodeQL | Medium: the test scans for image files, it does not assert the queue count |
| T2 | DepthAI telemetry, crash-dump upload or auto-calibration turns on | STRIDE I | `privacy.py` forces the three variables before `depthai` loads; `oak-events doctor` shows the state | Low: relies on DepthAI honouring its own variables |
| T3 | Someone reads event files and learns people's routines | STRIDE I | Files mode 0600; files never leave the host through oak-events | Medium: no encryption at rest and no automatic deletion (see `DATA_FLOW.md`) |
| T4 | A local process forges or edits event lines | STRIDE S, T | Owner-only file mode; the MCP server skips malformed lines | Medium: anyone with the same user account can write valid fake events; no integrity protection |
| T5 | Text in events carries instructions to the agent (prompt injection) | OWASP LLM01 | Events are flat JSON, mostly numeric; free text comes only from zone names (deployer config), model class labels (model archive), device metadata and error details (unexpected errors capped at 300 characters); tools return data, not instructions | Medium: a malicious zones file or model archive can still place text in front of an agent |
| T6 | An agent is given more power than reading events | OWASP LLM06 | Tools are read-only; no tool reaches the camera, the file system beyond the events directory, or the network | Low inside oak-events; deployers who add action tools own that risk |
| T7 | The MCP server reads files outside the events directory | STRIDE I, E | Tools take no path arguments; the server reads only `*.jsonl` in the configured directory | Low: a symbolic link placed inside the directory is followed |
| T8 | Very large event files slow or stop the MCP server | STRIDE D | Result limit of 500; health and zone tools read at most 14 daily files | Low: each read loads a whole daily file into memory |
| T9 | The detector is evaded (people not detected) or spoofed (photos, screens, mannequins detected as people) | ATLAS AML.T0015 Evade AI Model; AML.T0043 Craft Adversarial Data | Confirm frames (3), confidence threshold (0.5), gone timeout (10 s) reduce noise | High for adversarial use: not a security control. oak-events must not be used as a safety or security system (acceptable use policy) |
| T10 | A poisoned or tampered model archive | ATLAS AML.T0010 AI Supply Chain Compromise; AML.T0018 Manipulate AI Model | No download at runtime; the deployer fetches the archive once; the model runs on the camera and can only emit detections, so it cannot add a picture stream; reference archive hash published in `MODEL_CARD.md` | Medium: no signature or automatic hash check. **Commitment:** optional `--model-sha256` check by 2027-03-31 |
| T11 | Another host on the network connects to a PoE camera and reads its streams directly | STRIDE I, outside oak-events | `DATA_FLOW.md` tells deployers to keep the camera on an isolated network segment | Depends on the deployment |
| T12 | A malicious release or dependency | Supply chain | Actions pinned to commit SHAs; Dependabot; CodeQL; trusted publishing (no stored upload token); 2FA on the publishing account; no binaries in the repository | Medium: no branch protection yet (**Commitment** 2026-12-15); unsigned tags (**Commitment** 2027-01-31); dependency versions are ranges, not pins |
| T13 | A malformed zones file crashes the runner | STRIDE D | Zones are validated; errors exit with code 2 and a one-line message | Low |

## 3. Malicious instructions and malware

Policy for CloudLab Works and contributors:

1. Treat all text in events, model labels, configuration files, issues and pull requests as data, never as
   instructions.
2. oak-events will not add MCP tools that execute commands, fetch URLs, write files or return images.
3. Code and dependencies are scanned (CodeQL, Dependabot, secret scanning); the repository holds no binaries.
4. Maintainer endpoints run built-in anti-malware protection (security baseline, section 5).

Deployers should tell their agent that oak-events tool output is untrusted data.

## 4. Adversarial threats to the model

The reference detector (see `MODEL_CARD.md`) is a general object detector trained on COCO. It was not
hardened against adversarial inputs by CloudLab Works, and upstream hardening is UNKNOWN. Known practical
attacks: hiding from the camera (clothing, posture, lighting, partial occlusion), adversarial patches, and
showing images of people. oak-events limits the effect of a wrong detection to a wrong event; it does not
make decisions. These threats are reassessed at each review and when the reference model changes.

## 5. Out of scope

Physical tampering with the camera; compromise of the customer's host operating system; the agent's model
provider; Luxonis device firmware internals.
