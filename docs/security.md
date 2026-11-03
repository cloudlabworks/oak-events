# Security

## Reporting a vulnerability

Please report security issues **privately** through GitHub's security
advisories: open the repository's **Security** tab and choose
[**Report a vulnerability**](https://github.com/cloudlabworks/oak-events/security/advisories/new).
Do not open a public issue for security problems.

Include what you found, how to reproduce it, and the impact you expect. You
should get an acknowledgement within a week.

Reports are triaged, fixed and disclosed under the CloudLab Works
[incident response plan](https://github.com/cloudlabworks/.github/blob/main/policies/incident-response-plan.md),
which sets severity levels, fix targets and coordinated disclosure timelines.
Only the latest release receives fixes while the project is pre-1.0.

## In scope

Anything that breaks the [privacy model](README.md#privacy-model), for
example:

- a code path that sends colour frames to the host, or writes any image or
  depth map to disk,
- DepthAI telemetry, crash-dump upload or auto-calibration being enabled
  without `OAK_EVENTS_ALLOW_TELEMETRY=1`,
- the MCP server exposing anything other than event data, reading files outside
  the events directory, or touching the camera,
- event files being created with permissions broader than the owner.

## Verifying a release

PyPI serves PEP 740 publish attestations for every oak-events file it hosts,
including 0.1.2.

From the release after 0.1.2, each version tag builds the sdist and wheel
once, records build provenance for them through Sigstore, publishes them to
PyPI and attaches the same files and `oak_events-<version>.intoto.jsonl` to
the GitHub Release. To check a downloaded file:

```bash
gh attestation verify oak_events-<version>-py3-none-any.whl --repo cloudlabworks/oak-events
```

Add `--bundle oak_events-<version>.intoto.jsonl` to verify against the bundle
from the release instead of the GitHub attestations API.

## Security and AI documentation

| Document | What it covers |
| --- | --- |
| [Threat model](THREAT_MODEL.md) | Trust boundaries, threats (STRIDE, MITRE ATLAS, OWASP LLM Top 10) and residual risk |
| [Model card](MODEL_CARD.md) | The reference detector, its limits, failure modes and open-model risk |
| [Data flow, retention and privacy impact](DATA_FLOW.md) | What leaves the camera, what is stored, retention and redaction |
| [Software bill of materials](SBOM.md) | CycloneDX SBOM and licence summary for 0.1.2 |
| [Shared responsibility](SHARED_RESPONSIBILITY.md) | Who owns which security control (CloudLab Works, you, the model provider), per AI-CAIQ question |
| [Risk assessment](RISK_ASSESSMENT.md) | AI risk register and AI impact assessment |
| [Hardening](HARDENING.md) | Running oak-events as a dedicated user, with a sandboxed, read-only MCP server |

The CloudLab Works
[security policies](https://github.com/cloudlabworks/.github/tree/main/policies)
cover the security baseline, the security and AI governance policy (including
acceptable use of oak-events), the incident response plan, the supply chain
policy and the security program index.
