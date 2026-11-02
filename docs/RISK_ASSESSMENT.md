# oak-events AI risk assessment and AI impact assessment

| | |
| --- | --- |
| Owner and risk acceptor | Alex Alvord, founder, CloudLab Works |
| Version | Published 2026-11-02, written against oak-events 0.1.1 plus unreleased changes (commit c3075be) and the changes released in 0.1.2 |
| Status | Approved by Alex Alvord and published 2026-11-02. The residual risks in section 3 are accepted as of that date |
| Review | At least once a year (next by 2027-11-01) and on any trigger in section 1.5 |
| Related | [`THREAT_MODEL.md`](THREAT_MODEL.md), [`DATA_FLOW.md`](DATA_FLOW.md), [`MODEL_CARD.md`](MODEL_CARD.md), [`SHARED_RESPONSIBILITY.md`](SHARED_RESPONSIBILITY.md), CloudLab Works [governance policy](https://github.com/cloudlabworks/.github/blob/main/policies/security-and-ai-governance-policy.md) (section 8, acceptable use) |

This is the AI risk management program for oak-events: how risks are found, rated, owned, treated and
accepted (section 1), the current register (sections 2 and 3), and the AI impact assessment (section 4).
CloudLab Works is one person, so the founder sponsors the program, owns every CloudLab Works risk and is
the only person who can accept one.

## 1. Procedure

### 1.1 Identify

Sources, checked at each review: the threat model (every threat T1 to T13 has a risk here), the model
card's limits and failure modes, the data flow, vulnerability reports and incidents, Dependabot and code
scanning alerts, the supplier review (supply chain policy), the legal tracking table (governance policy
section 7), and new entries in MITRE ATLAS and the OWASP Top 10 for LLM Applications.

### 1.2 Evaluate

Likelihood and impact are each Low, Medium or High.

| | Impact Low | Impact Medium | Impact High |
| --- | --- | --- | --- |
| **Likelihood High** | Medium | High | High |
| **Likelihood Medium** | Low | Medium | High |
| **Likelihood Low** | Low | Low | Medium |

Impact is judged for the people in view of the camera first, then the deployer, then CloudLab Works.

### 1.3 Own

Each risk has one owner: **CloudLab Works** (fixed in the code, releases or documents), **Customer**
(fixed in the deployment), or **Shared** (both have actions; the split follows `SHARED_RESPONSIBILITY.md`).

### 1.4 Treat and accept

| Option | Use |
| --- | --- |
| Mitigate | Add or strengthen a control; record it in "Controls" with a date if not done |
| Avoid | Remove the feature or prohibit the use (acceptable use, governance policy section 8) |
| Transfer | Move the duty to the party able to act on it, and say so in `SHARED_RESPONSIBILITY.md` |
| Accept | Only if the residual rating is Low or Medium, by Alex, recorded in section 3 with the date |

A High residual risk cannot be accepted: it needs a dated treatment or an avoid decision.

### 1.5 Review

Once a year, and when any of these happens: a change to the event schema, MCP tools, host output queues,
privacy defaults or reference model; a new DepthAI major version; a security incident or vulnerability
report rated High or Critical; a change to a law in the governance policy's legal table; a supplier
trigger in the supply chain policy. Each review is a dated commit to this file, and its outcome feeds the
review of the acceptable use policy (governance policy section 8).

## 2. Risk register

L: likelihood, I: impact, R: residual rating after current controls. "Done" controls exist in the
published code or documents; "Planned" controls are published commitments with a date. Controls marked (L)
were released in oak-events 0.1.2.

| ID | Risk | Source | L | I | R | Owner | Treatment | Controls |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R1 | A code change sends pictures or depth maps to the host or to disk | T1 | Low | High | Medium | CloudLab Works | Mitigate | Done: two host queues only, `test_no_images.py`, `CONTRIBUTING.md` rule, ethics and privacy check (governance section 9), CodeQL. Planned: a test that asserts the host queue count, by 2027-03-31 |
| R2 | DepthAI telemetry, crash-dump upload or auto-calibration turns on without the deployer knowing | T2 | Low | Medium | Low | Shared | Mitigate | Done: `privacy.py` forces the variables; `doctor` shows them. (L): `privacy` event at each start and `private` in `camera_health`, alerting example |
| R3 | Someone with access to the host reads event files and learns people's routines | T3, DATA_FLOW 7 | Medium | High | High | Customer | Transfer, mitigate | Done: mode 0600 files, retention and redaction guidance, data flow privacy impact summary. (L): MCP access log; sandbox recipe in `HARDENING.md`. Planned: `--retain-days`, by 2027-03-31. Not acceptable as High; the planned control and the customer duties (retention, host access) bring it to Medium |
| R4 | Forged or edited event lines mislead an agent | T4 | Low | Medium | Low | Shared | Mitigate, accept | Done: owner-only files, malformed lines skipped. Accepted: no integrity protection on event lines |
| R5 | Prompt injection through zone names, model labels or error text | T5 | Low | Medium | Low | Shared | Mitigate | Done: flat JSON, capped error text, tools return data. Deployer tells the agent tool output is untrusted |
| R6 | An agent acts on events without a human (for example unlocks a door) | T6, OWASP LLM06 | Medium | High | High | Customer | Avoid, transfer | Done: read-only tools; acceptable use requires a human approval step before any action that affects a person; prohibited as a safety or security system. Residual stays High in deployments that ignore this; CloudLab Works cannot prevent it, so it is a deployer duty in `SHARED_RESPONSIBILITY.md` |
| R7 | The MCP server reads files outside the events directory | T7 | Low | High | Medium | CloudLab Works | Mitigate | Done: no path arguments, `*.jsonl` only. Remaining: a symbolic link inside the directory is followed. (L): read-only sandbox in `HARDENING.md`. Planned: refuse symbolic links, by 2027-03-31 |
| R8 | Large event files stop the MCP server | T8 | Low | Low | Low | CloudLab Works | Accept | Done: result limit 500, 14-day scan window |
| R9 | People are not detected, or photos are detected as people | T9, MODEL_CARD 3 and 4 | High | Medium | High for safety use, Medium otherwise | Shared | Avoid, mitigate | Done: confirm frames, threshold, gone timeout; safety and security use prohibited. (L): per-zone confidence statistics and the spot-check procedure (`MODEL_CARD.md` section 7) |
| R10 | A poisoned or swapped model archive | T10 | Low | High | Medium | Shared | Mitigate | Done: no runtime download; archive is a device blob, not host code; reference SHA-256 published. (L): `--model-sha256` refuses a mismatch; hash in every `camera` `up` event |
| R11 | A supplier fails, changes terms or is compromised, and CloudLab Works cannot enforce service levels | T12, supply chain policy | Low | Medium | Low | CloudLab Works | Accept, mitigate | Done: annual supplier review, hash-pinned CI tools, Dependabot, trusted publishing. Accepted: no negotiated service levels; customers run oak-events themselves, so a supplier outage does not stop a running deployment |
| R12 | A malicious release or dependency | T12 | Low | High | Medium | CloudLab Works | Mitigate | Done: Actions pinned by SHA, Dependabot, CodeQL, trusted publishing. Planned: branch protection 2026-12-15, signed tags 2027-01-31, SBOM in `release.yml` 2027-02-28 |
| R13 | A malformed zones file stops the runner | T13 | Low | Low | Low | CloudLab Works | Accept | Done: validation, exit code 2, fuzzing |
| R14 | A PoE camera is read directly by another host on the network | T11 | Medium | High | Depends on deployment | Customer | Transfer | Done: `DATA_FLOW.md` and `HARDENING.md` tell deployers to isolate the camera network |
| R15 | oak-events is used for covert monitoring, monitoring of employees or tenants, or in private spaces | Impact assessment 4.2 | Medium | High | High | Customer | Avoid | Done: prohibited uses (governance section 8); no identification, no pictures; notice duties. CloudLab Works cannot enforce this outside the shipped code; residual stays with the deployer |
| R16 | Someone adds identification (face recognition, re-identification) to a fork or a deployment | Impact assessment 4.1 | Low | High | Medium | Shared | Avoid | Done: prohibited use; contributions that add identification are refused; the event schema has no identity fields |
| R17 | Lower detection for some people (children, people lying down or using mobility aids, some clothing or skin tones) makes events less reliable for them | MODEL_CARD 8 | Medium | Medium | Medium | Shared | Mitigate | Done: limits documented; not for safety use. Planned: first CloudLab Works spot-check by 2027-03-31 (`MODEL_CARD.md` section 7) |
| R18 | Events retained indefinitely build a detailed pattern of life | DATA_FLOW 4 | High | Medium | High | Customer | Mitigate, transfer | Done: retention example in `DATA_FLOW.md`. Planned: `--retain-days`, by 2027-03-31. Deployer sets retention |
| R19 | Events reach the agent's model provider, outside the deployer's control | T6, B4 | High | Medium | High | Customer | Transfer | Done: documented in `DATA_FLOW.md` and the threat model. The deployer chooses the agent and provider; oak-events cannot reduce this |
| R20 | The only maintainer becomes unavailable and fixes stop | Governance section 2 | Low | Medium | Low | CloudLab Works | Mitigate | Done: open source, MIT licence, no hosted service, coordinated disclosure lets reporters publish. Planned: continuity plan by 2027-03-31 |
| R21 | A change in privacy or AI law makes a common deployment unlawful | Governance section 7 | Low | Medium | Low | Shared | Mitigate | Done: legal tracking table reviewed yearly and on change; deployer duty to check local law |

## 3. Acceptance

Residual risks rated Low or Medium and marked "Accept" or "Accepted" above (R4, R8, R11, R13, and the
accepted remainders of R2 and R5) are accepted by Alex Alvord **when this file is approved and
published**. The date of that commit is the acceptance date. High residual risks (R3, R6, R9 for safety
use, R15, R18, R19) are not accepted by CloudLab Works: each has a dated control, an avoid decision, or a
customer duty in `SHARED_RESPONSIBILITY.md`.

## 4. AI impact assessment

### 4.1 Method and criteria

The assessment covers the whole lifecycle: design (what the code can sense and output), release (what
ships and what defaults are on), deployment (where a camera is placed, who is told), operation (what is
stored, who and which agents read it), and retirement (deleting event files and the model file).

Each impact is rated by **severity** (how much harm to a person), **reach** (how many people, and
whether they chose to be there), **reversibility** (can the harm be undone), and **likelihood** (Low,
Medium or High, as in section 1.2). People in view of the camera are assessed first: they did not
choose oak-events and may not know it is running.

It is repeated at each review (section 1.5) and before any change that triggers the ethics and privacy
check in the governance policy (section 9). Results feed the risk register (section 2), the acceptable
use policy (governance policy section 8) and the shared-responsibility guide.

### 4.2 Assessment

Assessment of 2026-11-02 for oak-events 0.1.1 plus the changes released in 0.1.2.

| Dimension | Who is affected | Impact | Severity, reach, reversibility | Likelihood | Mitigations | Residual and owner |
| --- | --- | --- | --- | --- | --- | --- |
| Ethical: consent and notice | Household members, guests, workers in view | Presence and routines recorded without real consent, especially guests and children | Medium severity; few people per camera; harm to trust is hard to undo | Medium | No pictures, no identities; notice duty and prohibited covert use (governance section 8) | Medium; customer |
| Ethical: function creep toward identification | People in view | Events joined with other data, or a fork adds face recognition, to single out a person | High severity; irreversible once identities are linked | Low | Prohibited use; refused contributions; no identity fields; no image path to the host | Medium; shared (R16) |
| Societal: home monitoring | Partners, children, carers, guests | Monitoring inside a home can be used for control or coercion between household members | High severity for the person monitored; hard to reverse | Low to Medium | Prohibited covert monitoring and monitoring in private spaces; events show presence, not activity | Medium; customer (R15) |
| Societal: workplace monitoring | Employees, contractors | Presence and dwell times used to judge work, in places where law or agreements forbid it | Medium to High severity; affects a whole team | Low (product is aimed at homes and labs) | Prohibited where local law does not allow it; decisions with significant effect from events alone are prohibited | Medium; customer (R15) |
| Societal: public spaces | Passers-by | Camera covers a street, hallway or shared space; people cannot opt out | Medium severity; unknown reach | Low | Intended use is the deployer's own space with the knowledge of its users | Low; customer |
| Operational: wrong detections | Deployer, people relying on automations | Missed or false person events cause wrong automations (lights, alerts, messages) | Low to Medium severity; reversible | High | Confirm frames, threshold, timeout; not a safety system; (L) confidence statistics and spot-check | Medium; shared (R9) |
| Operational: agent actions | People affected by an agent's action | An agent acts on an event without a human check | Up to High severity depending on the action | Medium | Read-only tools; human approval step required by acceptable use | High where ignored; customer (R6) |
| Operational: availability | Deployer | Camera or runner stops; health tool shows it | Low severity | Medium | Supervisor restart, `camera_health`, reconnect logic | Low; shared |
| Legal | Deployer, people in view, CloudLab Works | Deployment breaks privacy, recording-notice or workplace law; licence breach on model redistribution | Medium to High for the deployer | Low | Legal tracking table (not legal advice); DPIA guidance in `DATA_FLOW.md`; GPL-3.0 note in `MODEL_CARD.md` | Low for CloudLab Works; Medium for deployers who do not check local law (R21) |
| Privacy | People in view | Pattern of life from long retention; disclosure of absence (burglary risk); events sent to an agent's model provider | Medium to High; disclosure is irreversible | Medium | Files 0600; no telemetry; retention guidance and planned `--retain-days`; redaction recipe; (L) access log | High until retention is set; customer (R3, R18, R19) |
| Security | People in view, deployer | Tampered model, malicious release, local file access, PoE stream exposure | Medium to High | Low | Threat model T1 to T13 and their controls; (L) model hash check | Medium; shared (R10, R12, R14) |
| Fairness | Children, people lying down, wheelchair users, people in unusual clothing or poses, some skin tones in low light | Fewer or later events for them, so automations work less well for them | Medium severity; reversible | Medium | Known limits documented with sources (`MODEL_CARD.md` section 8); not for safety or care use; spot-check procedure | Medium; shared (R17) |

### 4.3 Communication

This file is public in the oak-events repository and linked from the README. Material changes are noted
in `CHANGELOG.md`. Deployers are asked to repeat section 4.2 for their own site; the privacy impact
summary in `DATA_FLOW.md` section 7 is a starting point.
