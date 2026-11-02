# Test bed for docs/HARDENING.md: Debian 13 (trixie) with systemd as PID 1.
# Not a deployment image. Build context: this directory, with the oak-events wheel and
# the files under test copied in by test.sh.
FROM debian:trixie
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends systemd systemd-sysv dbus sudo \
      python3 python3-venv ca-certificates jq && rm -rf /var/lib/apt/lists/*
COPY oak_events-*.whl /tmp/
RUN python3 -m venv /opt/oak-events/venv \
 && /opt/oak-events/venv/bin/pip install -q /tmp/oak_events-*.whl numpy 'mcp>=1.0'
COPY oak-events-run.service /etc/systemd/system/oak-events-run.service
COPY oak-events-mcp-sandbox /usr/local/bin/oak-events-mcp-sandbox
COPY in-container.sh /root/in-container.sh
COPY model.tar.xz /etc/oak-events/yolov6n-r2-288x512.rvc2.tar.xz
RUN chmod 0755 /usr/local/bin/oak-events-mcp-sandbox /root/in-container.sh \
 && useradd --system --home-dir /var/lib/oak-events --shell /usr/sbin/nologin oak-events \
 && useradd --create-home alice \
 && printf 'alice ALL=(root) NOPASSWD: /usr/local/bin/oak-events-mcp-sandbox\n' > /etc/sudoers.d/oak-events-mcp \
 && chmod 0440 /etc/sudoers.d/oak-events-mcp \
 && chmod 0644 /etc/oak-events/yolov6n-r2-288x512.rvc2.tar.xz
STOPSIGNAL SIGRTMIN+3
CMD ["/lib/systemd/systemd"]
