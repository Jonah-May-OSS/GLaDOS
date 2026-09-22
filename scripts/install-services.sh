#!/usr/bin/env bash
set -euo pipefail

INSTALL_ROOT="${INSTALL_ROOT:-/opt/glados}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Installing GLaDOS files to ${INSTALL_ROOT}..."

sudo mkdir -p "${INSTALL_ROOT}/sounds"
sudo mkdir -p "${INSTALL_ROOT}/services"

sudo cp -a "${REPO_ROOT}/services/." "${INSTALL_ROOT}/services/"
sudo cp -a "${REPO_ROOT}/sounds/." "${INSTALL_ROOT}/sounds/" 2>/dev/null || true

# The three startup clips are one ordered boot sequence. Remove the old
# split services so an upgrade cannot play the sequence twice.
sudo systemctl disable --now glados-powerup.service glados-wakeup.service 2>/dev/null || true
sudo rm -f /etc/systemd/system/glados-powerup.service /etc/systemd/system/glados-wakeup.service

sudo install -m 0644 "${REPO_ROOT}/services/glados-boot-sounds.service" /etc/systemd/system/glados-boot-sounds.service
sudo install -m 0644 "${REPO_ROOT}/services/glados-display.service" /etc/systemd/system/glados-display.service

sudo systemctl daemon-reload
sudo systemctl enable glados-boot-sounds.service
sudo systemctl enable --now glados-display.service

echo
echo "Installed and enabled:"
echo "  glados-boot-sounds.service"
echo "  glados-display.service"
