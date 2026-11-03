# oak-events shared security responsibility model (SSRM)

| | |
| --- | --- |
| Owner and approver | Alex Alvord, CloudLab Works |
| Version | Approved by Alex Alvord and published 2026-11-02 with the CloudLab Works AI-CAIQ (CSA AI-CAIQ v1.1.0, AI Controls Matrix v1.1.1) |
| Source | The ownership column (D) and customer-responsibility column (F) of the CloudLab Works AI-CAIQ, one row per question, in [`ssrm-ownership-ai-caiq-v1.1.0.csv`](ssrm-ownership-ai-caiq-v1.1.0.csv) |
| Review | At every release, and at least once a year with the AI-CAIQ refresh (next by 2027-11-01) |

oak-events is open source software that the customer installs and runs on their own camera and host.
CloudLab Works runs no hosted service and receives no data from it (see [`DATA_FLOW.md`](DATA_FLOW.md)).
That fixes the split: CloudLab Works owns what it writes, ships and documents; the customer owns
everything about the deployment; the model provider owns the detector's training and build.

## 1. Parties

| Party | Who | Owns |
| --- | --- | --- |
| Application provider | CloudLab Works (Cloud Lab Works LLC) | oak-events code, releases, documentation, security fixes, vulnerability handling, the privacy defaults, the reference-model guidance in `MODEL_CARD.md`, its own accounts and devices |
| Customer (deployer) | The person or organization that runs oak-events | The camera, the host, the network, the event files and their retention, notice to people in view, the choice of model file, the choice of AI agent and its model provider, access to the host, incident handling in the deployment |
| Model provider | For the reference model: Meituan (developer) and Luxonis (converts and distributes it in the Luxonis model zoo). For any other model: whoever the customer gets it from | Training data, training pipeline, model hardening, model evaluation, the archive's content |
| Platform suppliers to CloudLab Works | GitHub (code, CI, advisories), PyPI (packages), Luxonis (DepthAI SDK and device firmware), upstream Python packages, Cloudflare (DNS and hosting for cloudlabworks.dev only, not the product) | Their own services, under their published terms. CloudLab Works reviews them as set out in the [supply chain policy](https://github.com/cloudlabworks/.github/blob/main/policies/supply-chain-policy.md) |
| Agent and its model provider | Chosen by the customer | Whatever the agent does with events it reads, and whatever its model provider keeps. Outside oak-events (`THREAT_MODEL.md`, boundary B4) |

## 2. Ownership per AICM domain

Count of AI-CAIQ questions per owner. CLW: CloudLab Works. Shared: CloudLab Works and the customer each
do part. Customer: the customer does all of it. Model provider and Supply chain: the model provider
does it, or it is shared along the model supply chain. Platform: a platform provider. NA: the control
does not apply to oak-events (the AI-CAIQ gives the reason per question).

| Domain | CLW | Shared | Customer | Model provider | Supply chain | Platform | NA | Total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Audit & Assurance (A&A) | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 7 |
| Application & Interface Security (AIS) | 12 | 4 | 1 | 0 | 0 | 0 | 1 | 18 |
| Business Continuity Management and Operational Resilience (BCR) | 9 | 1 | 3 | 0 | 0 | 0 | 3 | 16 |
| Change Control and Configuration Management (CCC) | 8 | 2 | 1 | 0 | 0 | 0 | 0 | 11 |
| Cryptography, Encryption & Key Management (CEK) | 4 | 0 | 3 | 0 | 0 | 1 | 15 | 23 |
| Datacenter Security (DCS) | 4 | 0 | 14 | 0 | 0 | 0 | 10 | 28 |
| Data Security and Privacy Lifecycle Management (DSP) | 7 | 10 | 4 | 5 | 0 | 0 | 4 | 30 |
| Governance, Risk and Compliance (GRC) | 16 | 1 | 0 | 0 | 1 | 0 | 0 | 18 |
| Human Resources (HRS) | 1 | 0 | 0 | 0 | 0 | 0 | 21 | 22 |
| Identity & Access Management (IAM) | 18 | 3 | 1 | 0 | 0 | 0 | 0 | 22 |
| Interoperability & Portability (IPY) | 3 | 0 | 1 | 0 | 0 | 0 | 1 | 5 |
| Infrastructure Security (I&S) | 0 | 0 | 9 | 0 | 0 | 0 | 4 | 13 |
| Logging and Monitoring (LOG) | 3 | 12 | 3 | 0 | 0 | 0 | 3 | 21 |
| Model Security (MDS) | 5 | 7 | 0 | 2 | 5 | 0 | 0 | 19 |
| Security Incident Management, E-Discovery, & Cloud Forensics (SEF) | 16 | 0 | 0 | 0 | 0 | 0 | 0 | 16 |
| Supply Chain Management, Transparency, and Accountability (STA) | 18 | 0 | 0 | 0 | 0 | 0 | 1 | 19 |
| Threat & Vulnerability Management (TVM) | 16 | 1 | 0 | 0 | 0 | 0 | 0 | 17 |
| Universal Endpoint Management (UEM) | 12 | 1 | 0 | 0 | 0 | 0 | 2 | 15 |
| **All domains** | **159** | **42** | **40** | **7** | **6** | **1** | **65** | **320** |

### Customer duties by domain

**Audit & Assurance (A&A)**

- Customers may review the published Scorecard and this AI-CAIQ; assurance over their own deployment is theirs.
- Customers needing independent assurance should perform or commission their own review of the open source code.
- Verify the legal requirements that apply to your own camera deployment (notice, consent, retention).

**Application & Interface Security (AIS)**

- Apply your own application security policy to how you deploy and integrate oak-events.
- None for the baseline; keep event files and the events directory owner-only as shipped.
- Test new versions on your own hardware before upgrading production deployments.
- Install a pinned version, run oak-events under a supervisor that restarts it (README 'Running it for real', https://github.com/cloudlabworks/oak-events/blob/1732fbb/README.md) and own the deployment configuration.
- Report suspected vulnerabilities privately as described in SECURITY.md (https://github.com/cloudlabworks/oak-events/blob/1732fbb/SECURITY.md); watch releases and CHANGELOG.md for fixes and upgrade promptly.
- Restrict who can start the MCP server and read the events directory; configure tool approval in your MCP client.
- Keep the zones file and model file under your control.
- Keep the events directory writable only by the account that runs 'oak-events run'.
- Define the agent's other tools and permissions in your MCP client; oak-events only bounds its own tools.
- Run the MCP server and agent tools in an isolated environment with read-only access to the events directory.
- Treat oak-events tool output as untrusted data in your agent's prompts (zone names and labels come from your configuration and model).

**Business Continuity Management and Operational Resilience (BCR)**

- Keep a copy of the release you run and of your model file.
- Run oak-events under a supervisor (systemd, launchd, container restart policy) and keep the release and model file you depend on.
- Watch the repository releases to receive notices.
- Back up event files, zones file and model file according to your own policy.
- Protect and test restores of your own backups.
- Provide redundant cameras or hosts if your use case needs them.

**Change Control and Configuration Management (CCC)**

- Review the CHANGELOG before upgrading.
- Decide when to upgrade; pin the version you run.
- Record the configuration you deploy.
- Alert on the startup privacy event once available.
- Pin versions and keep the previous version available for rollback.

**Cryptography, Encryption & Key Management (CEK)**

- Use full-disk encryption on the host and keep the PoE camera on a trusted, isolated network segment.
- Manage your own keys.
- Generate keys in your environment with approved libraries.

**Datacenter Security (DCS)**

- Secure the premises, camera and host physically.
- Wipe hosts and storage that held event files before disposal.
- Control transfers of your own hosts and event files.
- Restrict which devices can reach the camera network.

**Data Security and Privacy Lifecycle Management (DSP)**

- Apply your data lifecycle policy to event files.
- Delete event files securely when retiring storage.
- Inventory where your deployment stores event files.
- Classify event files under your own scheme (sensitive at minimum).
- Document any further flows you add (webhooks, agent logs).
- Name an owner for event data in your organization.
- Review your data ownership annually.
- Keep event files local.
- Meet recording, notice and consent laws where the camera is installed.
- Run your own DPIA where law requires.
- Protect any forwarding you configure and isolate the camera link.
- Handle data-subject requests for your event files.
- Declare and keep to the purpose of your camera deployment.
- Set and enforce a retention period for event files. See DATA_FLOW.md section 4 for a cleanup recipe.
- Encrypt the host disk and restrict access to the events directory.
- Choose and record where event files are stored.
- Record which model file and device you deploy.
- Choose detection models from a provider whose training-data practices you accept.

**Governance, Risk and Compliance (GRC)**

- Identify the requirements that apply to your deployment.
- Use oak-events within the acceptable-use policy and local law. Follow the acceptable use policy (governance policy section 8).
- Assess the impact of your own deployment.
- Check detection quality on the people and scenes in your deployment.
- Decide the explainability your use case needs.
- Account for these limits in agent behaviour.
- Keep a human in control of any actions your agent takes on oak-events data.

**Identity & Access Management (IAM)**

- Run oak-events under an unprivileged account.
- Control privileged access in your environment.
- Control which accounts can run oak-events and read the events directory.
- Give agents only the oak-events access they need.
- Restrict write access to the events directory.
- Grant agents only the MCP servers they need.

**Interoperability & Portability (IPY)**

- Retrieve your data directly from the events directory.
- Use secure protocols for any forwarding you add.

**Infrastructure Security (I&S)**

- Apply your own organization's policy for this control to the host, camera and event files of your deployment.
- Size the host for the camera pipeline.
- Isolate the PoE camera on a trusted network segment; restrict who can reach it.
- Harden the host OS.
- Separate deployments for different parties.
- Identify the camera network and event store as sensitive in your environment.
- Apply network defence to the host and camera network.

**Logging and Monitoring (LOG)**

- Back up and retain event files according to your policy.
- Monitor security events once emitted.
- Wire security alerts into your monitoring.
- Restrict and record access to the events directory.
- Correlate oak-events and host logs in your own monitoring.
- Define your own anomaly response.
- Synchronize the host clock (NTP).
- Decide which events you keep and forward.
- Redact device ids before sharing event files. Use the DATA_FLOW.md section 5 recipe before sharing event files.
- Enable and retain the access log once available.
- Protect the events directory against modification and deletion.
- Act on camera_health and camera events.
- Wire the notifications to the people accountable.
- Log agent tool calls in your MCP client if needed.
- Retain the event files you need for audit.

**Model Security (MDS)**

- Choose models from providers with a secure training pipeline.
- As MDS-01.1.
- Verify the model file before use.
- Document the model you deploy.
- Assess adversarial risk at your site.
- Pin and verify the model hash.
- Load models only from trusted sources.
- Spot-check detections on your scene.
- Decide what a missed or false event means for your use case.
- Run under a supervisor and alert on camera_health.
- Assess the open model you choose. Assess the open model you choose; see MODEL_CARD.md section 5.
- Use NNArchive files from trusted sources.

**Security Incident Management, E-Discovery, & Cloud Forensics (SEF)**

- Handle incidents in your own deployment.
- Report suspected vulnerabilities privately as described in SECURITY.md (https://github.com/cloudlabworks/oak-events/blob/1732fbb/SECURITY.md); watch releases and CHANGELOG.md for fixes and upgrade promptly.

**Supply Chain Management, Transparency, and Accountability (STA)**

- Read the shared-responsibility guide and implement the customer-owned controls.
- Use the SBOM in your own vulnerability management.

**Threat & Vulnerability Management (TVM)**

- Report suspected vulnerabilities privately as described in SECURITY.md (https://github.com/cloudlabworks/oak-events/blob/1732fbb/SECURITY.md); watch releases and CHANGELOG.md for fixes and upgrade promptly.
- Treat tool output as data, not instructions, in your agent. Tell your agent that oak-events tool output is untrusted data.
- Scan your own host and installed packages.
- Threat-model your deployment (camera placement, network, agent).
- Update your installed copy when a release updates dependencies.
- Penetration-test your own deployment if required.
- Add guardrails in your agent runtime for actions taken on events.

**Universal Endpoint Management (UEM)**

- Manage your own hosts that store event files (encryption, patching, lock screen).
- Check your OS, Python and camera against the supported list.

### Questions the customer owns or shares

| Question | Control | Owner | What the customer does |
| --- | --- | --- | --- |
| AIS-06.1 | Secure Application Deployment | Shared: CloudLab Works and customer | Install a pinned version, run oak-events under a supervisor that restarts it (README 'Running it for real', https://github.com/cloudlabworks/oak-events/blob/1732fbb/README.md) and own the deployment configuration. |
| AIS-08.1 | API Security | Shared: CloudLab Works and customer | Restrict who can start the MCP server and read the events directory; configure tool approval in your MCP client. |
| AIS-11.1 | Agents Security Boundaries | Shared: CloudLab Works and customer | Define the agent's other tools and permissions in your MCP client; oak-events only bounds its own tools. |
| AIS-13.1 | AI Sandboxing | Shared: CloudLab Works and customer | Run the MCP server and agent tools in an isolated environment with read-only access to the events directory. |
| AIS-15.1 | Prompt Differentiation | Customer | Treat oak-events tool output as untrusted data in your agent's prompts (zone names and labels come from your configuration and model). |
| BCR-03.1 | Business Continuity Strategy | Shared: CloudLab Works and customer | Run oak-events under a supervisor (systemd, launchd, container restart policy) and keep the release and model file you depend on. |
| BCR-08.1 | Backup | Customer | Back up event files, zones file and model file according to your own policy. |
| BCR-08.2 | Backup | Customer | Protect and test restores of your own backups. |
| BCR-11.1 | Equipment Redundancy | Customer | Provide redundant cameras or hosts if your use case needs them. |
| CCC-05.1 | Change Agreements | Customer | Decide when to upgrade; pin the version you run. |
| CCC-07.1 | Detection of Baseline Deviation | Shared: CloudLab Works and customer | Alert on the startup privacy event once available. |
| CCC-09.1 | Change Restoration | Shared: CloudLab Works and customer | Pin versions and keep the previous version available for rollback. |
| CEK-03.1 | Data Protection | Customer | Use full-disk encryption on the host and keep the PoE camera on a trusted, isolated network segment. |
| CEK-04.1 | Encryption Algorithm | Customer | Use full-disk encryption on the host and keep the PoE camera on a trusted, isolated network segment. |
| CEK-08.1 | Service Customer Key Management Capability | Customer | Manage your own keys. |
| CEK-10.1 | Key Generation | Platform provider | Generate keys in your environment with approved libraries. |
| DCS-01.1 | Physical and Environmental Security Policy and Procedures | Customer | Secure the premises, camera and host physically. |
| DCS-01.2 | Physical and Environmental Security Policy and Procedures | Customer | Secure the premises, camera and host physically. |
| DCS-02.1 | Off-Site Equipment Disposal Policy and Procedures | Customer | Wipe hosts and storage that held event files before disposal. |
| DCS-02.2 | Off-Site Equipment Disposal Policy and Procedures | Customer | Wipe hosts and storage that held event files before disposal. |
| DCS-02.3 | Off-Site Equipment Disposal Policy and Procedures | Customer | Wipe hosts and storage that held event files before disposal. |
| DCS-03.1 | Off-Site Transfer Authorization Policy and Procedures | Customer | Control transfers of your own hosts and event files. |
| DCS-03.2 | Off-Site Transfer Authorization Policy and Procedures | Customer | Control transfers of your own hosts and event files. |
| DCS-03.3 | Off-Site Transfer Authorization Policy and Procedures | Customer | Control transfers of your own hosts and event files. |
| DCS-04.1 | Secure Area Policy and Procedures | Customer | Secure the premises, camera and host physically. |
| DCS-04.2 | Secure Area Policy and Procedures | Customer | Secure the premises, camera and host physically. |
| DCS-08.1 | Controlled Physical Access Points | Customer | Secure the premises, camera and host physically. |
| DCS-09.1 | Equipment Identification | Customer | Restrict which devices can reach the camera network. |
| DCS-10.1 | Secure Area Authorization | Customer | Secure the premises, camera and host physically. |
| DCS-10.2 | Secure Area Authorization | Customer | Secure the premises, camera and host physically. |
| DSP-02.1 | Secure Disposal | Customer | Delete event files securely when retiring storage. |
| DSP-03.1 | Data Inventory | Shared: CloudLab Works and customer | Inventory where your deployment stores event files. |
| DSP-04.1 | Data Classification | Shared: CloudLab Works and customer | Classify event files under your own scheme (sensitive at minimum). |
| DSP-05.1 | Data Flow Documentation | Shared: CloudLab Works and customer | Document any further flows you add (webhooks, agent logs). |
| DSP-06.1 | Data Ownership and Stewardship | Shared: CloudLab Works and customer | Name an owner for event data in your organization. |
| DSP-06.2 | Data Ownership and Stewardship | Shared: CloudLab Works and customer | Review your data ownership annually. |
| DSP-09.1 | Data Protection Impact Assessment | Shared: CloudLab Works and customer | Run your own DPIA where law requires. |
| DSP-10.1 | Sensitive Data Transfer | Customer | Protect any forwarding you configure and isolate the camera link. |
| DSP-11.1 | Personal Data Access, Reversal, Rectification and Deletion | Customer | Handle data-subject requests for your event files. |
| DSP-12.1 | Limitation of Purpose in Personal Data Processing | Customer | Declare and keep to the purpose of your camera deployment. |
| DSP-16.1 | Data Retention and Deletion | Shared: CloudLab Works and customer | Set and enforce a retention period for event files. See DATA_FLOW.md section 4 for a cleanup recipe. |
| DSP-17.1 | Sensitive Data Protection | Shared: CloudLab Works and customer | Encrypt the host disk and restrict access to the events directory. |
| DSP-19.1 | Data Location | Shared: CloudLab Works and customer | Choose and record where event files are stored. |
| DSP-20.1 | Data Provenance and Transparency | Shared: CloudLab Works and customer | Record which model file and device you deploy. |
| DSP-21.1 | Data Poisoning Prevention & Detection | Model provider | Choose detection models from a provider whose training-data practices you accept. |
| DSP-22.1 | Privacy Enhancing Technologies | Model provider | Choose detection models from a provider whose training-data practices you accept. |
| DSP-23.1 | Data Integrity Check | Model provider | Choose detection models from a provider whose training-data practices you accept. |
| DSP-23.2 | Data Integrity Check | Model provider | Choose detection models from a provider whose training-data practices you accept. |
| DSP-24.1 | Data Differentiation and Relevance | Model provider | Choose detection models from a provider whose training-data practices you accept. |
| GRC-11.1 | Bias and Fairness Assessment | Shared across the supply chain | Check detection quality on the people and scenes in your deployment. |
| GRC-15.1 | Human supervision | Shared: CloudLab Works and customer | Keep a human in control of any actions your agent takes on oak-events data. |
| IAM-11.1 | Service Customers' Approval for Agreed Privileged Access Roles | Customer | Control privileged access in your environment. |
| IAM-15.1 | Authorization Mechanisms | Shared: CloudLab Works and customer | Control which accounts can run oak-events and read the events directory. |
| IAM-17.1 | Output Modification and Special Authorization | Shared: CloudLab Works and customer | Restrict write access to the events directory. |
| IAM-18.1 | Agent Access Restriction | Shared: CloudLab Works and customer | Grant agents only the MCP servers they need. |
| IPY-03.1 | Secure Interoperability and Portability Management | Customer | Use secure protocols for any forwarding you add. |
| I&S-01.1 | Infrastructure and Virtualization Security Policy and Procedures | Customer | Apply your own organization's policy for this control to the host, camera and event files of your deployment. |
| I&S-01.2 | Infrastructure and Virtualization Security Policy and Procedures | Customer | Apply your own organization's policy for this control to the host, camera and event files of your deployment. |
| I&S-02.1 | Capacity and Resource Planning | Customer | Size the host for the camera pipeline. |
| I&S-03.1 | Network Security | Customer | Isolate the PoE camera on a trusted network segment; restrict who can reach it. |
| I&S-03.2 | Network Security | Customer | Apply your own organization's policy for this control to the host, camera and event files of your deployment. |
| I&S-04.1 | OS Hardening and Base Controls | Customer | Harden the host OS. |
| I&S-06.1 | Segmentation and Segregation | Customer | Separate deployments for different parties. |
| I&S-08.1 | Network Architecture Documentation | Customer | Identify the camera network and event store as sensitive in your environment. |
| I&S-09.1 | Network Defense | Customer | Apply network defence to the host and camera network. |
| LOG-02.1 | Audit Logs Protection | Shared: CloudLab Works and customer | Back up and retain event files according to your policy. |
| LOG-03.1 | Security Monitoring and Alerting | Shared: CloudLab Works and customer | Monitor security events once emitted. |
| LOG-03.2 | Security Monitoring and Alerting | Shared: CloudLab Works and customer | Wire security alerts into your monitoring. |
| LOG-04.1 | Audit Logs Access and Accountability | Shared: CloudLab Works and customer | Restrict and record access to the events directory. |
| LOG-05.1 | Audit Logs Monitoring and Response | Customer | Correlate oak-events and host logs in your own monitoring. |
| LOG-05.2 | Audit Logs Monitoring and Response | Customer | Define your own anomaly response. |
| LOG-06.1 | Clock Synchronization | Customer | Synchronize the host clock (NTP). |
| LOG-07.1 | Logging Scope | Shared: CloudLab Works and customer | Decide which events you keep and forward. |
| LOG-08.1 | Audit Logs Sanitization | Shared: CloudLab Works and customer | Redact device ids before sharing event files. Use the DATA_FLOW.md section 5 recipe before sharing event files. |
| LOG-09.1 | Log Records | Shared: CloudLab Works and customer | Enable and retain the access log once available. |
| LOG-10.1 | Audit Records Protection | Shared: CloudLab Works and customer | Protect the events directory against modification and deletion. |
| LOG-14.1 | Failures and Anomalies Reporting | Shared: CloudLab Works and customer | Act on camera_health and camera events. |
| LOG-14.2 | Failures and Anomalies Reporting | Shared: CloudLab Works and customer | Wire the notifications to the people accountable. |
| LOG-15.1 | Input Monitoring | Shared: CloudLab Works and customer | Log agent tool calls in your MCP client if needed. |
| LOG-16.1 | Output Monitoring | Shared: CloudLab Works and customer | Retain the event files you need for audit. |
| MDS-01.1 | Training Pipeline Security | Model provider | Choose models from providers with a secure training pipeline. |
| MDS-01.2 | Training Pipeline Security | Model provider | As MDS-01.1. |
| MDS-02.1 | Model Artifact Scanning | Shared across the supply chain | Verify the model file before use. |
| MDS-02.2 | Model Artifact Scanning | Shared across the supply chain | No customer action for this control; it concerns CloudLab Works' own practices. |
| MDS-06.1 | Adversarial Attack Analysis | Shared across the supply chain | Assess adversarial risk at your site. |
| MDS-07.1 | Robustness against Adversarial Attack / Model Hardening | Shared across the supply chain | No customer action for this control; it concerns CloudLab Works' own practices. |
| MDS-08.1 | Model Integrity Checks | Shared: CloudLab Works and customer | Pin and verify the model hash. |
| MDS-08.2 | Model Integrity Checks | Shared: CloudLab Works and customer | No customer action for this control; it concerns CloudLab Works' own practices. |
| MDS-09.1 | Model Signing/Ownership Verification | Shared across the supply chain | Load models only from trusted sources. |
| MDS-10.1 | Model Continuous Monitoring | Shared: CloudLab Works and customer | Spot-check detections on your scene. |
| MDS-11.2 | Model Failure | Shared: CloudLab Works and customer | Run under a supervisor and alert on camera_health. |
| MDS-12.1 | Open Model Risk Assessment | Shared: CloudLab Works and customer | Assess the open model you choose. Assess the open model you choose; see MODEL_CARD.md section 5. |
| MDS-12.2 | Open Model Risk Assessment | Shared: CloudLab Works and customer | No customer action for this control; it concerns CloudLab Works' own practices. |
| MDS-13.1 | Secure Model Format | Shared: CloudLab Works and customer | Use NNArchive files from trusted sources. |
| TVM-13.1 | Guardrails | Shared: CloudLab Works and customer | Add guardrails in your agent runtime for actions taken on events. |
| UEM-03.1 | Compatibility | Shared: CloudLab Works and customer | Check your OS, Python and camera against the supported list. |

## 3. How customers are told

1. This document is linked from the README ("Security and AI documentation").
2. The per-question split is published twice: in the CSV next to this file and in the CloudLab Works
   AI-CAIQ on the CSA STAR Registry.
3. A release that moves a duty between CloudLab Works and the customer (for example a new option that
   the customer must turn on) says so in `CHANGELOG.md` under the release, and updates this file in the
   same pull request.

## 4. How the model is applied and kept current

1. **Each change.** A pull request that changes the MCP tools, the event schema, the host output
   queues, the privacy defaults or the reference model (the changes that already need a security and
   privacy review, security baseline section 7) also answers: does this move a duty between CloudLab
   Works, the customer and the model provider? If yes, it updates the CSV and section 2 here.
2. **Each release.** The release checklist (security baseline section 7) includes: regenerate section 2
   from the CSV and check that every AI-CAIQ question has exactly one owner value.
3. **Each year.** With the AI-CAIQ self-assessment (governance policy section 6), Alex re-reads every
   row, checks the owner against the code and documents of the release in scope, and records the
   review as a dated commit to this file and the CSV.
4. **Validation.** The CSV is checked against the submitted AI-CAIQ before each submission: same 320
   question IDs, same owner and customer-responsibility text. A difference is fixed before submission.
5. **Supply chain.** Duties that sit with the model provider or a platform supplier are checked in the
   annual supplier review (supply chain policy section 5). If a supplier stops doing its part (for
   example the model zoo stops publishing a model's provenance), the gap is recorded in
   `RISK_ASSESSMENT.md` and this file says what the customer should do instead.

## 5. Assessment of CloudLab Works' part

CloudLab Works assesses its own part (every question owned by CLW or shared) once a year in the AI-CAIQ
self-assessment. Each NO answer has a corrective plan, an owner and a date, and is tracked as a public
GitHub issue labelled `csa-remediation` until closed (governance policy section 6). An independent
review is planned (governance policy section 2).
