#!/bin/bash
# Runs inside the test container (systemd is PID 1). Prints PASS/FAIL lines.
set -u
fail=0
pass() { echo "PASS: $*"; }
bad() { echo "FAIL: $*"; fail=1; }
EV=/var/lib/oak-events/events

echo "== systemd $(systemctl --version | head -1)"
systemd-analyze verify /etc/systemd/system/oak-events-run.service 2>&1 | grep -v 'Unit configured to use KillMode' || true

echo "== 1. runner service: hash check passes, events written as oak-events, mode 0600"
systemctl daemon-reload
systemctl start oak-events-run.service
sleep 4
systemctl stop oak-events-run.service
f=$(ls "$EV"/*.jsonl 2>/dev/null | head -1)
if [ -n "$f" ] && grep -q '"kind": "privacy"' "$f"; then pass "privacy event written to $f"; else bad "no privacy event"; fi
grep -q '"private": true' "$f" && pass "privacy state private=true" || bad "private not true"
[ "$(stat -c '%U %a' "$f")" = "oak-events 600" ] && pass "event file owner oak-events, mode 600" || bad "file owner/mode $(stat -c '%U %a' "$f")"
[ "$(stat -c '%U %a' "$EV")" = "oak-events 700" ] && pass "events dir owner oak-events, mode 700" || bad "dir $(stat -c '%U %a' "$EV")"
journalctl -u oak-events-run.service --no-pager -o cat | grep -q 'depthai is not installed' \
  && pass "runner got past the model hash check (stopped at missing depthai, expected in this test bed)" \
  || bad "runner did not reach depthai import"

echo "== 2. runner sandbox probe: same [Service] sandbox options, as oak-events"
props=()
while IFS= read -r line; do props+=(-p "$line"); done < <(
  awk '/^\[Service\]/{s=1;next} /^\[/{s=0} s && /^[A-Z][A-Za-z]*=/' /etc/systemd/system/oak-events-run.service |
  grep -vE '^(ExecStart|Type|Restart|RestartSec|User|Group)=')
probe='touch /var/lib/oak-events/events/probe && echo W_EVENTS_OK; touch /etc/probe 2>/dev/null && echo W_ETC_OK; ls /home/alice >/dev/null 2>&1 && echo R_HOME_OK; touch /tmp/probe && echo W_TMP_OK; /opt/oak-events/venv/bin/python -c "import os; os.setuid(0)" 2>/dev/null && echo SETUID_OK; true'
out=$(systemd-run --quiet --pipe --wait --collect --uid=oak-events --gid=oak-events "${props[@]}" /bin/sh -c "$probe" 2>&1)
echo "$out" | grep -q W_EVENTS_OK && pass "runner can write the events directory" || bad "runner cannot write events: $out"
echo "$out" | grep -q W_ETC_OK && bad "runner can write /etc" || pass "runner cannot write /etc"
echo "$out" | grep -q R_HOME_OK && bad "runner can read /home" || pass "runner cannot read /home"
echo "$out" | grep -q SETUID_OK && bad "runner can setuid(0)" || pass "runner cannot gain root"
rm -f /var/lib/oak-events/events/probe

echo "== 3. runner refuses a wrong model hash"
cp /etc/systemd/system/oak-events-run.service /tmp/bad.service
sed -i 's/--model-sha256 [0-9a-f]*/--model-sha256 0000000000000000000000000000000000000000000000000000000000000000/' /tmp/bad.service
cp /tmp/bad.service /etc/systemd/system/oak-events-badhash.service
systemctl daemon-reload; systemctl start oak-events-badhash.service; sleep 3; systemctl stop oak-events-badhash.service
grep -h 'SHA-256 mismatch' "$EV"/*.jsonl >/dev/null && pass "mismatch event written, camera not opened" || bad "no mismatch event"
rm /etc/systemd/system/oak-events-badhash.service; systemctl daemon-reload

echo "== 4. MCP server through the sandbox wrapper, started by desktop user alice with sudo"
req='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"test","version":"0"}}}
{"jsonrpc":"2.0","method":"notifications/initialized"}
{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"camera_health","arguments":{}}}
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"recent_events","arguments":{"limit":5}}}'
resp=$( (printf '%s\n' "$req"; sleep 4) | timeout 30 sudo -u alice sudo -n /usr/local/bin/oak-events-mcp-sandbox 2>&1)
echo "$resp" | grep -q '\\"private\\": true' && pass "camera_health over MCP reports private=true" || bad "MCP response: $resp"
echo "$resp" | grep -q '"id":3' && pass "recent_events answered" || bad "no recent_events answer"
log=/var/log/oak-events/mcp-access.jsonl
[ -f "$log" ] && [ "$(wc -l < "$log")" -ge 2 ] && pass "access log has $(wc -l < "$log") lines" || bad "access log missing"
[ "$(stat -c '%U %a' "$log")" = "oak-events 600" ] && pass "access log owner oak-events, mode 600" || bad "log $(stat -c '%U %a' "$log")"
jq -e 'select(.tool=="recent_events") | .args.limit == 1 and .result_count >= 1' "$log" >/dev/null \
  && pass "access log: argument size and result count, no values" || bad "access log content: $(cat "$log")"
sudo -u alice cat "$EV"/*.jsonl >/dev/null 2>&1 && bad "alice can read event files directly" || pass "alice cannot read event files directly"

echo "== 5. MCP sandbox probe: same properties as the wrapper"
sed -n '1,/oak-events\/venv\/bin\/oak-events mcp/p' /usr/local/bin/oak-events-mcp-sandbox | sed '$d' > /tmp/probe.sh
probe2='touch /var/lib/oak-events/events/x 2>/dev/null && echo W_EVENTS_OK; cat /var/lib/oak-events/events/*.jsonl >/dev/null && echo R_EVENTS_OK; touch /var/log/oak-events/x && echo W_LOG_OK; ls /home/alice >/dev/null 2>&1 && echo R_HOME_OK; /opt/oak-events/venv/bin/python -c "import socket; s=socket.socket(); s.settimeout(2); s.connect((\"1.1.1.1\", 443))" 2>/dev/null && echo NET_OK; ls /dev | wc -l | sed "s/^/DEVCOUNT=/"; true'
printf '  /bin/sh -c %q\n' "$probe2" >> /tmp/probe.sh
out=$(bash /tmp/probe.sh 2>&1)
echo "$out" | grep -q R_EVENTS_OK && pass "MCP sandbox can read events" || bad "cannot read events: $out"
echo "$out" | grep -q W_EVENTS_OK && bad "MCP sandbox can write events" || pass "MCP sandbox cannot write the events directory (read-only)"
echo "$out" | grep -q W_LOG_OK && pass "MCP sandbox can write its access log directory" || bad "cannot write log dir"
echo "$out" | grep -q R_HOME_OK && bad "MCP sandbox can read /home" || pass "MCP sandbox cannot read /home"
echo "$out" | grep -q NET_OK && bad "MCP sandbox has network" || pass "MCP sandbox has no network"
if runuser -u oak-events -- /opt/oak-events/venv/bin/python -c 'import socket; s=socket.socket(); s.settimeout(3); s.connect(("1.1.1.1", 443))' 2>/dev/null; then
  pass "control: the same connect works outside the sandbox, so the network result above is the sandbox's doing"
else
  echo "NOTE: control connect failed outside the sandbox too; the network result above proves nothing in this test bed"
fi
echo "$out" | grep DEVCOUNT
rm -f /var/log/oak-events/x

echo "== 6. exposure scores (systemd-analyze security; lower is better)"
systemd-analyze security oak-events-run.service --no-pager 2>/dev/null | tail -1

echo "== RESULT: $([ $fail = 0 ] && echo ALL PASS || echo FAILURES)"
exit $fail
