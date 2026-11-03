# Hardening an oak-events deployment

| | |
| --- | --- |
| Owner | Alex Alvord, CloudLab Works |
| Version | Approved by Alex Alvord and published 2026-11-02. Needs oak-events 0.1.2 or later (`--model-sha256`, `--access-log`) |
| Review | At each release that changes a command line option, the MCP tools or the files oak-events writes, and at least once a year (next by 2027-11-01) |
| Files | [`examples/hardening/`](../examples/hardening/): `oak-events-run.service`, `oak-events-mcp-sandbox`, `test/` |

oak-events already limits itself: no pictures leave the camera, the MCP server has three read-only tools
and no path arguments, and event files are owner-only. This guide adds operating-system isolation, so
that a bug in oak-events, in DepthAI or in an agent's use of the MCP tools cannot reach the rest of the
host. It is the customer's part of AI-CAIQ AIS-13.1 (see `SHARED_RESPONSIBILITY.md`).

The recipe is for Linux with systemd. It was tested in a container (section 5), not with a camera.

## 1. Layout

| Path | Owner and mode | Who writes it | Who reads it |
| --- | --- | --- | --- |
| `/opt/oak-events/venv` | root, 0755 | Install step only | Both services |
| `/etc/oak-events/` (model archive, zones file) | root, 0644 files | Admin only | Runner |
| `/var/lib/oak-events/events/` | `oak-events`, 0700; files 0600 | Runner only | MCP server, read-only |
| `/var/log/oak-events/mcp-access.jsonl` | `oak-events`, 0700 directory; file 0600 | MCP server | Admin |

Two processes, one dedicated system user, `oak-events`, with no login shell. The runner can write only the
events directory. The MCP server can write only its access log: the events directory is read-only to it,
and it has no network at all.

## 2. Install

```bash
sudo useradd --system --home-dir /var/lib/oak-events --shell /usr/sbin/nologin oak-events
sudo python3 -m venv /opt/oak-events/venv
sudo /opt/oak-events/venv/bin/pip install 'oak-events[camera,mcp]'   # pin the version you tested
sudo install -d -m 0755 /etc/oak-events
sudo install -m 0644 yolov6n-r2-288x512.rvc2.tar.xz /etc/oak-events/
```

Verify the model archive first (`MODEL_CARD.md` section 2.1) and put its SHA-256 in the unit file.

## 3. Runner: a sandboxed system service

Copy `examples/hardening/oak-events-run.service` to `/etc/systemd/system/`, edit the model path, hash and
options, then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now oak-events-run.service
journalctl -u oak-events-run.service -f
```

What the unit does:

- runs as `oak-events`, with `NoNewPrivileges`, no capabilities, and a system call filter
  (`@system-service`);
- `ProtectSystem=strict`, `ProtectHome=yes`, `PrivateTmp=yes`: the whole file system is read-only or
  hidden except the state directory `/var/lib/oak-events/events`, created by systemd with mode 0700;
- `UMask=0077`, so nothing it creates is readable by other users;
- `--model-sha256`: refuses to start if the model archive changed;
- `--quiet`: events go only to the event files, not to the journal (otherwise the journal keeps a
  second copy of every event; `DATA_FLOW.md` section 3);
- network limited to IPv4, IPv6, netlink and Unix sockets, which a PoE camera needs. For a USB camera, use
  the commented lines instead: no network at all, and only USB devices.

**Not tested with a camera.** The unit was tested without DepthAI and without a camera (section 5). If
DepthAI fails under it, read the journal for `SECCOMP` or address-family errors and relax one option at a
time; please report what you had to change.

## 4. MCP server: read-only, no network, started on demand

An MCP client starts the server over stdio, so it is not a long-running service. The wrapper
`examples/hardening/oak-events-mcp-sandbox` starts it as a transient systemd unit with `systemd-run
--pipe`, which passes stdin and stdout through to the client:

- runs as `oak-events` (the only user that can read the 0600 event files);
- `ReadOnlyPaths=/var/lib/oak-events`: it can read events but cannot change or add any;
- `PrivateNetwork=yes`, `IPAddressDeny=any`, Unix sockets only: no network;
- `PrivateDevices=yes`, `ProtectHome=yes`, `ProtectSystem=strict`, no capabilities, system call filter,
  memory and task limits;
- `--access-log /var/log/oak-events/mcp-access.jsonl`: one line per tool call (tool, argument sizes,
  result count, outcome, client process id), never values or results. The log directory is the only
  writable path.

`systemd-run` needs root, so the desktop user who runs the MCP client gets one `sudo` rule for this exact
command, which takes no arguments:

```bash
sudo install -m 0755 oak-events-mcp-sandbox /usr/local/bin/
echo 'alice ALL=(root) NOPASSWD: /usr/local/bin/oak-events-mcp-sandbox' | sudo tee /etc/sudoers.d/oak-events-mcp
sudo chmod 0440 /etc/sudoers.d/oak-events-mcp
sudo visudo -c
```

Replace `alice` with the user. Client configuration (same shape as `examples/claude-desktop-mcp.json`):

```json
{"mcpServers": {"oak-events": {"command": "sudo", "args": ["-n", "/usr/local/bin/oak-events-mcp-sandbox"]}}}
```

If the MCP client runs on another computer, use `ssh` as the command (`ssh HOST sudo -n
/usr/local/bin/oak-events-mcp-sandbox`); stdio passes through ssh.

## 5. Test results

`bash examples/hardening/test/test.sh WHEEL MODEL` builds a Debian 13 container with systemd as PID 1,
installs oak-events from a wheel, and checks the two recipes. Run on 2026-11-02 with a wheel built from the
code released in oak-events 0.1.2 (branch `csa/logging-integrity`) and the reference model archive; all 23 checks passed:

| Check | Result |
| --- | --- |
| Runner starts as `oak-events`, passes the model hash check, writes the `privacy` event | Pass |
| Event files owned by `oak-events`, mode 0600; directory mode 0700 | Pass |
| Runner can write the events directory, cannot write `/etc`, cannot read `/home`, cannot gain root | Pass |
| A wrong `--model-sha256` stops the runner with a mismatch event, camera not opened | Pass |
| MCP server through the wrapper, started by a desktop user with `sudo`: `camera_health` and `recent_events` answer; `private` is `true` | Pass |
| Access log written, owned by `oak-events`, mode 0600, with argument sizes and result counts only | Pass |
| The desktop user cannot read event files directly | Pass |
| MCP sandbox can read events and write its log, cannot write the events directory, cannot read `/home`, has no network (the same connection works outside the sandbox) | Pass |
| `systemd-analyze security oak-events-run.service` | 1.7 ("OK"; lower is better) |

Not tested: a real camera, DepthAI under these options, USB device access, other distributions.

## 6. Also recommended

1. **Camera network.** Put a PoE camera on its own network segment or VLAN that only the oak-events host
   can reach (`DATA_FLOW.md` section 2). Nothing else needs to talk to it.
2. **Direct file access.** The MCP access log records reads through MCP, not someone running `cat` on
   the files. To record those too, add a Linux audit rule, for example
   `auditctl -w /var/lib/oak-events/events -p rwa -k oak-events`, and keep it in `/etc/audit/rules.d/`.
   Not tested by CloudLab Works.
3. **Retention.** Delete old event files on a timer (`DATA_FLOW.md` section 4); run the timer as
   `oak-events`.
4. **Alerts.** Forward `privacy` events with `"private": false` and `camera` errors to someone who will
   read them (`examples/webhook.md`).
5. **Updates.** Pin the oak-events and DepthAI versions you tested; update both deliberately and re-run
   the model spot-check (`MODEL_CARD.md` section 7) after a DepthAI update.

macOS (launchd) is not covered yet.
