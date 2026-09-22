#!/usr/bin/env bash
set -euo pipefail

INSTALL_ROOT="${INSTALL_ROOT:-/opt/glados}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Installing GLaDOS files to ${INSTALL_ROOT}..."

sudo mkdir -p "\${INSTALL_ROOT}/sounds"
sudo mkdir -p "\${INSTALL_ROOT}/services"

sudo cp -a "\${REPO_ROOT}/services/." "\${INSTALL_ROOT}/services/"
sudo cp -a "\${REPO_ROOT}/sounds/." "\${INSTALL_ROOT}/sounds/" 2>/dev/null || true

# Keep systemd journal growth bounded so the Pi cannot fill its storage with
# service logs. These limits apply to the system journal as a whole.
sudo mkdir -p /etc/systemd/journald.conf.d
sudo tee /etc/systemd/journald.conf.d/20-glados-retention.conf >/dev/null <<'EOF'
[Journal]
SystemMaxUse=200M
SystemKeepFree=500M
RuntimeMaxUse=100M
MaxRetentionSec=30day
EOF

sudo systemctl restart systemd-journald
sudo journalctl --vacuum-time=30d --vacuum-size=200M

# The boot sequence is intentionally split into an early power-up stage and
# a late wake-up stage. Remove the temporary unified service from older
# installations so it cannot play the sequence a second time.
sudo systemctl disable --now glados-boot-sounds.service 2>/dev/null || true
sudo rm -f /etc/systemd/system/glados-boot-sounds.service

sudo install -m 0644 "${REPO_ROOT}/services/glados-powerup.service" /etc/systemd/system/glados-powerup.service
sudo install -m 0644 "${REPO_ROOT}/services/glados-wakeup.service" /etc/systemd/system/glados-wakeup.service
sudo install -m 0644 "${REPO_ROOT}/services/glados-display.service" /etc/systemd/system/glados-display.service

sudo systemctl daemon-reload
sudo systemctl enable glados-powerup.service
sudo systemctl enable glados-wakeup.service
sudo systemctl enable --now glados-display.service

echo
echo "Installed and enabled:"
echo "  glados-powerup.service"
echo "  glados-wakeup.service"
echo "  glados-display.service"
