#!/usr/bin/env bash
set -euo pipefail

INSTALL_ROOT="${INSTALL_ROOT:-/opt/glados}"
SOUND_DIR="${INSTALL_ROOT}/sounds"

mkdir -p "${SOUND_DIR}"

download() {
  local url="$1"
  local destination="$2"
  echo "Downloading ${destination}..."
  curl -fL --retry 3 --output "${SOUND_DIR}/${destination}" "${url}"
}

download "https://i1.theportalwiki.net/img/d/de/Announcer_wakeup_powerup01.wav" "powerup01.wav"
download "https://i1.theportalwiki.net/img/a/a1/Announcer_wakeup_powerup02.wav" "powerup02.wav"
download "https://i1.theportalwiki.net/img/3/34/GLaDOS_chellgladoswakeup01.wav" "glados_wakeup.wav"

echo "Sounds installed in ${SOUND_DIR}"
