#!/bin/bash
# Build the test bed and run in-container.sh under systemd. Usage:
#   test.sh WHEEL MODEL_ARCHIVE
# WHEEL: an oak-events wheel built from the csa/logging-integrity branch (needs --model-sha256
# and --access-log). MODEL_ARCHIVE: the reference archive from docs/MODEL_CARD.md.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
ctx=$(mktemp -d)
cp "$here/Dockerfile" "$here/in-container.sh" "$here/../oak-events-run.service" "$here/../oak-events-mcp-sandbox" "$ctx/"
cp "$1" "$ctx/"
cp "$2" "$ctx/model.tar.xz"
docker build -q -t oak-events-hardening-test "$ctx" >/dev/null
cid=$(docker run -d --privileged --cgroupns=host -v /sys/fs/cgroup:/sys/fs/cgroup:rw --tmpfs /run --tmpfs /run/lock \
  oak-events-hardening-test)
trap 'docker rm -f "$cid" >/dev/null; rm -rf "$ctx"' EXIT
for _ in $(seq 1 30); do
  state=$(docker exec "$cid" systemctl is-system-running 2>/dev/null || true)
  case "$state" in running|degraded) break ;; esac
  sleep 1
done
docker exec "$cid" /root/in-container.sh
