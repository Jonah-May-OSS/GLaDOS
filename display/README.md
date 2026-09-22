# Display

The physical GLaDOS display uses the Waveshare 1.28-inch LCD Module with a GC9A01 controller and 240×240 IPS panel.

## Hardware

The display is connected to the Raspberry Pi over SPI.

| Display | Raspberry Pi |
|---|---|
| VCC | 3.3V — pin 1 |
| GND | GND — pin 6 |
| DIN | GPIO10 / MOSI — pin 19 |
| CLK | GPIO11 / SCLK — pin 23 |
| CS | GPIO8 / CE0 — pin 24 |
| DC/DS | GPIO25 — pin 22 |
| RST | GPIO27 — pin 13 |
| BL | GPIO18 — pin 12 |

SPI must be enabled on the Raspberry Pi.

## Software

The display uses the official Waveshare Python driver for the hardware layer. The GLaDOS renderer loads the source-derived aperture sprite and maps voice-assistant states to animations.

The display controller connects to the Linux Voice Assistant (LVA) peripheral WebSocket API on port 6055. LVA exposes the Home Assistant voice-assistant state through this interface, so no Home Assistant access token or separate HA API integration is required.

LVA events are mapped as follows:

| LVA event | Display |
|---|---|
| `wake_word_detected` | Aperture opening |
| `listening` | Listening animation |
| `thinking` | Thinking animation |
| `tts_speaking` | Speaking animation |
| `idle` / `tts_finished` | Idle |
| `pipeline_error` | Error flash |
| `disconnected` | Connection-lost pulse |

The controller automatically reconnects to LVA if the container restarts or the network/HA connection is temporarily unavailable.

## Installation

The top-level installer handles the display dependencies, Waveshare driver, display files, and systemd service:

```bash
./scripts/install.sh
```

The service starts automatically at boot:

```bash
sudo systemctl status glados-display.service
```

For manual testing:

```bash
sudo systemctl restart glados-display.service
```

Logs:

```bash
journalctl -u glados-display.service -f
```

LVA must have its peripheral API enabled on port 6055, which is the default.
