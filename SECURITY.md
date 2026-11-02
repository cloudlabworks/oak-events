# Security policy

## Reporting a vulnerability

Please report security issues **privately** through GitHub's security
advisories: open the repository's **Security** tab and choose **Report a
vulnerability**. Do not open a public issue for security problems.

Include what you found, how to reproduce it, and the impact you expect. You
should get an acknowledgement within a week.

## How reports are handled

Reports are triaged, fixed and disclosed under the CloudLab Works
[incident response plan](https://github.com/cloudlabworks/.github/blob/main/policies/incident-response-plan.md),
which sets severity levels, fix targets and coordinated disclosure timelines.
The [threat model](docs/THREAT_MODEL.md) lists the threats this project
defends against.

## In scope

Anything that breaks the privacy model described in the README, for example:

- a code path that sends colour frames to the host, or writes any image or
  depth map to disk,
- DepthAI telemetry, crash-dump upload or auto-calibration being enabled
  without `OAK_EVENTS_ALLOW_TELEMETRY=1`,
- the MCP server exposing anything other than event data, reading files outside
  the events directory, or touching the camera,
- event files being created with permissions broader than the owner.

## Supported versions

Only the latest release receives fixes while the project is pre-1.0.
