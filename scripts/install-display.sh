#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL_DIR="/opt/glados/display/waveshare"
ZIP_URL="https://files.waveshare.com/upload/8/8d/LCD_Module_RPI_code.zip"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

echo "Installing display dependencies..."
sudo apt-get update
sudo apt-get install -y python3-pil python3-numpy python3-rpi.gpio python3-spidev unzip wget

echo "Downloading Waveshare LCD driver..."
wget -q "$ZIP_URL" -O "$TMP_DIR/LCD_Module_RPI_code.zip"
unzip -q "$TMP_DIR/LCD_Module_RPI_code.zip" -d "$TMP_DIR"
SOURCE_DIR="$TMP_DIR/LCD_Module_RPI_code/RaspberryPi/python"
[[ -f "$SOURCE_DIR/lib/LCD_1inch28.py" ]] || { echo "ERROR: Waveshare LCD_1inch28.py not found." >&2; exit 1; }

sudo mkdir -p "$INSTALL_DIR"
sudo rm -rf "$INSTALL_DIR/lib"
sudo cp -a "$SOURCE_DIR/lib" "$INSTALL_DIR/"
sudo mkdir -p /opt/glados/display
sudo cp "$REPO_ROOT"/display/{__init__.py,states.py,driver.py,glados_display.py} /opt/glados/display/
sudo chown -R administrator:administrator /opt/glados/display

echo "Display software installed under /opt/glados/display"
echo "Run: cd /opt/glados/display && python3 glados_display.py"
