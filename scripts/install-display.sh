#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
INSTALL_DIR="/opt/glados/display"
WAVESHARE_DIR="$INSTALL_DIR/waveshare"
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

sudo mkdir -p "$WAVESHARE_DIR"
sudo rm -rf "$WAVESHARE_DIR/lib"
sudo cp -a "$SOURCE_DIR/lib" "$WAVESHARE_DIR/"
sudo mkdir -p "$INSTALL_DIR"
sudo cp -a "$REPO_ROOT/display/." "$INSTALL_DIR/"
sudo chown -R administrator:administrator "$INSTALL_DIR"

echo "Display software installed under $INSTALL_DIR"
echo "Run: cd /opt/glados && python3 -m display.glados_display"
