# oak-events threat model

| | |
| --- | --- |
| Owner | Alex Alvord, CloudLab Works |
| Version | Published 2026-11-02; written against commit 00d9053 (oak-events 0.1.1 plus unreleased changes). Revised, approved by Alex Alvord and published 2026-11-02: mitigation map (section 6) and guardrail review (section 7), against commit c3075be plus the changes released in 0.1.2 |
| Review | At least once a year (next by 2027-11-01) and whenever the event schema, MCP tools, host output queues, privacy defaults, reference model or DepthAI major version change; guardrails also on the triggers in section 7 |
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
| T2 | DepthAI telemetry, crash-dump upload or auto-calibration turns on | STRIDE I | `privacy.py` forces the three variables before `depthai` loads; `oak-events doctor` shows the state; every run writes a `privacy` event and `camera_health` reports `private` (from 0.1.2) | Low: relies on DepthAI honouring its own variables |
| T3 | Someone reads event files and learns people's routines | STRIDE I | Files mode 0600; files never leave the host through oak-events | Medium: no encryption at rest and no automatic deletion (see `DATA_FLOW.md`) |
| T4 | A local process forges or edits event lines | STRIDE S, T | Owner-only file mode; the MCP server skips malformed lines; `HARDENING.md` runs the runner as a dedicated user and the MCP server read-only | Medium: anyone with the same user account can write valid fake events; no integrity protection |
| T5 | Text in events carries instructions to the agent (prompt injection) | OWASP LLM01 | Events are flat JSON, mostly numeric; free text comes only from zone names (deployer config), model class labels (model archive), device metadata and error details (unexpected errors capped at 300 characters); tools return data, not instructions | Medium: a malicious zones file or model archive can still place text in front of an agent |
| T6 | An agent is given more power than reading events | OWASP LLM06 | Tools are read-only; no tool reaches the camera, the file system beyond the events directory, or the network | Low inside oak-events; deployers who add action tools own that risk |
| T7 | The MCP server reads files outside the events directory | STRIDE I, E | Tools take no path arguments; the server reads only `*.jsonl` in the configured directory; the `HARDENING.md` sandbox makes everything outside the events and log directories read-only or hidden | Low: a symbolic link placed inside the directory is followed |
| T8 | Very large event files slow or stop the MCP server | STRIDE D | Result limit of 500; health and zone tools read at most 14 daily files | Low: each read loads a whole daily file into memory |
| T9 | The detector is evaded (people not detected) or spoofed (photos, screens, mannequins detected as people) | ATLAS AML.T0015 Evade AI Model; AML.T0043 Craft Adversarial Data | Confirm frames (3), confidence threshold (0.5), gone timeout (10 s) reduce noise | High for adversarial use: not a security control. oak-events must not be used as a safety or security system (acceptable use policy) |
| T10 | A poisoned or tampered model archive | ATLAS AML.T0010 AI Supply Chain Compromise; AML.T0018 Manipulate AI Model | No download at runtime; the deployer fetches the archive once; the model runs on the camera and can only emit detections, so it cannot add a picture stream; reference archive hash published in `MODEL_CARD.md`; optional `--model-sha256` refuses a mismatch and every `camera` `up` event records the archive hash (from 0.1.2) | Medium: no signature; the hash check is off unless the deployer sets it |
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

## 6. Mitigations mapped to threats

Each mitigation, the threats it addresses, who operates it, and how it is evaluated. "0.1.2"
marks the changes released in oak-events 0.1.2 (branch `csa/logging-integrity`).

| Mitigation | Threats | Layer | Evaluated by |
| --- | --- | --- | --- |
| Only two host queues (detections, depth); colour frames never linked to the host | T1 | oak-events code | `tests/test_no_images.py`; review rule in `CONTRIBUTING.md` |
| Depth map reduced to cell medians and dropped | T1, T3 | oak-events code | `tests/test_depth_change.py`; code review |
| Privacy variables forced before `depthai` loads | T2 | oak-events code | `tests/test_privacy.py` |
| `privacy` event per run; `private` in `camera_health`; alerting example (0.1.2) | T2 | oak-events code, deployer alerting | `tests/test_logging_integrity.py` |
| Event files mode 0600; one append per line | T3, T4 | oak-events code | `tests/test_sink.py` |
| Malformed lines skipped; parsing fuzzed | T4, T8, T13 | oak-events code | `tests/test_parsing_robustness.py`; Atheris harness (`fuzz` workflow, 60 s per push) |
| Flat JSON events; error detail capped at 300 characters; tools return data | T5 | oak-events code | Code review; `tests/test_mcp_tools.py` |
| Read-only MCP tools with no path arguments | T6, T7 | oak-events code | `tests/test_mcp_tools.py` (tool list) |
| Result limit 500; 14-day scan window | T8 | oak-events code | `tests/test_mcp_tools.py` |
| MCP access log, off by default (0.1.2) | T3, T6 | oak-events code, deployer | `tests/test_logging_integrity.py` |
| Sandbox recipe: dedicated user, read-only events for the MCP server, no network for it (`HARDENING.md`) | T3, T4, T6, T7 | Deployer | Tested in a Debian 13 container under systemd 257 on 2026-11-02 (`HARDENING.md` section 5) |
| Confirm frames (3), confidence threshold (0.5), gone timeout (10 s) | T9 | oak-events code | `tests/test_person_tracker.py` |
| Per-zone confidence statistics and spot-check procedure (0.1.2; `MODEL_CARD.md` section 7) | T9, T10 | oak-events code, deployer | `tests/test_logging_integrity.py`; the spot-check itself |
| Not a safety or security system (acceptable use) | T9 | Policy, deployer | Annual acceptable use review (governance policy section 8) |
| No model download at runtime; device blob cannot run host code | T10 | oak-events code, model format | `MODEL_CARD.md` section 5; code review |
| Published SHA-256 of the tested archive; `--model-sha256` (0.1.2) | T10 | oak-events docs and code, deployer | `MODEL_CARD.md` section 2 verification command; `tests/test_logging_integrity.py` |
| Camera on an isolated network segment | T11 | Deployer | Deployer's own check |
| Actions pinned by SHA; Dependabot; CodeQL; trusted publishing; hash-pinned CI tools | T12 | CloudLab Works release process | Scorecard weekly; monthly alert review (governance policy section 6) |
| Zones validation with exit code 2 | T13 | oak-events code | `tests/test_parsing_robustness.py`; fuzzing |

**Adversarial threats to the model** (MITRE ATLAS, section 4):

| ATLAS technique | Threat | What CloudLab Works does | What it does not do |
| --- | --- | --- | --- |
| AML.T0015 Evade AI Model | T9 (hiding from the camera) | Limits the effect to a missing event; prohibits safety and security use; confidence statistics show drift | Does not harden the model; upstream hardening is UNKNOWN |
| AML.T0043 Craft Adversarial Data | T9 (patches, photos, screens) | Confirm frames and threshold reduce single-frame spoofs; spot-check procedure includes a photo test | No adversarial training or input filtering |
| AML.T0010 AI Supply Chain Compromise | T10 | Hash pinning, no runtime download, documented provenance | No signature (none offered upstream) |
| AML.T0018 Manipulate AI Model | T10 | Same as AML.T0010; the model runs on the camera and can only emit detections | No model scanning beyond the archive member check in `MODEL_CARD.md` |

CloudLab Works does not train or modify the model, so it cannot harden the model itself. The measures
above limit what an attack on the model can do to events and to the people in view. **Commitment:** ask
the model provider about adversarial robustness, and prefer a reference model with a published robustness
evaluation at the next model review, by 2027-11-01 (owner: Alex Alvord).

## 7. Guardrail review

Guardrails are the controls that limit what oak-events and the agents reading it can do: no pictures
to the host (T1), forced privacy defaults (T2), owner-only files (T3), read-only tools with no path
arguments and a result limit (T6 to T8), capped error text (T5), the model hash check (T10), and the
acceptable use prohibitions (governance policy section 8).

**When.** Once a year with this threat model, and within 30 days of any of these triggers:

1. a change to a law or standard in the governance policy's legal tracking table (section 7), or a new
   law the annual legal check adds to it;
2. a new version of the OWASP Top 10 for LLM Applications, or new MITRE ATLAS techniques for object
   detectors or agent tools;
3. a security incident or vulnerability report rated High or Critical, or a reported misuse of
   oak-events;
4. a new MCP tool, event field, host output queue, reference model or DepthAI major version;
5. a new risk, or a change in rating, in `RISK_ASSESSMENT.md`.

**What is checked.** For each guardrail: is it still enforced (its test still exists and passes in CI),
is it still enough for the risk scenarios in `RISK_ASSESSMENT.md`, and does any tracked law or standard
now ask for more. A guardrail found weak gets a dated fix in section 2 and in the risk register.

**Record.** Each review is a dated commit to this table.

| Review | Trigger | Result |
| --- | --- | --- |
| 2026-11-02 | First review, with the AI-CAIQ | All guardrails enforced by tests (section 6). Added: `privacy` event, model hash check, MCP access log, sandbox recipe. Open: symbolic links in the events directory (T7), no integrity protection for event lines (T4) |

