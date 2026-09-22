#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Installing GLaDOS..."
"${REPO_ROOT}/scripts/download-sounds.sh"
"${REPO_ROOT}/scripts/install-display.sh"
"${REPO_ROOT}/scripts/install-services.sh"

echo
echo "GLaDOS installation complete."
echo "Display service: sudo systemctl status glados-display.service"
