#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Installing GLaDOS system services..."
"${REPO_ROOT}/scripts/download-sounds.sh"
"${REPO_ROOT}/scripts/install-services.sh"

echo
echo "GLaDOS base installation complete."
