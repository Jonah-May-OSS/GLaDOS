# GLaDOS

A physical GLaDOS-inspired voice assistant head built around a Raspberry Pi, Home Assistant, Linux Voice Assistant (LVA), and a small SPI display.

## Overview

This repository contains the software that runs on the physical GLaDOS endpoint:

- A display renderer for the Waveshare 1.28-inch GC9A01 LCD
- Integration with LVA's peripheral WebSocket API
- Boot and startup sound services
- Installation scripts for the Pi
- Display artwork and supporting assets

The Raspberry Pi acts as the local hardware endpoint. Home Assistant and the voice-assistant services provide the higher-level voice pipeline.

### Architecture

~~~text
USB audio
   │
   ▼
Linux Voice Assistant
   ├── wake-word detection
   ├── ESPHome API ───────────────► Home Assistant
   └── peripheral WebSocket API
                 │
                 ▼
          GLaDOS display
~~~

The display does not connect directly to Home Assistant. It listens to LVA events over the peripheral WebSocket API.

## Hardware

### Reference hardware

The current build uses:

- Raspberry Pi 4 Model B
- Waveshare 1.28-inch 240×240 GC9A01 LCD
- USB microphone/speaker
- Raspberry Pi SPI interface

The repository also contains planned integration for servos and an addressable LED ring, but those components are not required to run the current display and audio software.

### Display wiring

For the current Waveshare GC9A01 module:

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

SPI must be enabled before installing the display software. On Raspberry Pi OS, run:\n\n~~~bash\nsudo raspi-config\n~~~\n\nSelect **Interface Options → SPI** and enable it, then reboot if prompted. Verify that the SPI device exists before continuing:\n\n~~~bash\nls /dev/spidev0.*\n~~~

The display implementation uses the official Waveshare Python driver as a hardware dependency. The driver is downloaded by the display installation script rather than committed to this repository.

## Prerequisites

Before installing this repository, provide the following:

### Raspberry Pi

- Raspberry Pi with a supported 64-bit Debian-based OS
- Python 3.13 or newer
- Git
- Working network access
- SPI enabled
- A user account that will own and run the GLaDOS services

### Audio

- A USB microphone/speaker or other supported audio device
- PipeWire with the PulseAudio compatibility layer (pipewire-pulse)
- The audio device working from the host before starting LVA

Verify the host can see the audio device with:

~~~bash
pactl info
~~~

If pactl is not available, install/configure the host's PipeWire/PulseAudio tools before continuing.

### LVA

Install and configure [Linux Voice Assistant](https://github.com/OHF-Voice/linux-voice-assistant) separately. Follow its installation documentation for Docker, Compose, audio access, and LVA configuration rather than duplicating those instructions here.

LVA must:

1. Be running on the same host.
2. Have access to the host audio device.
3. Expose its peripheral WebSocket API.
4. Provide the wake-word/audio functionality required by the overall voice-assistant setup.

The GLaDOS display defaults to:

~~~text
ws://127.0.0.1:6055
~~~

Set "LVA_WS_URL" if LVA is running somewhere else.

### Home Assistant

Home Assistant is not required by the display process itself, but it is part of the intended voice-assistant architecture. Configure the LVA ESPHome device and Home Assistant Assist pipeline according to the LVA and Home Assistant documentation.

## Installation

Clone the repository:

~~~bash
git clone https://github.com/Jonah-May-OSS/GLaDOS.git
cd GLaDOS
~~~

Run the installer as the user that should own the installation:

~~~bash
./scripts/install.sh
~~~

The installer:

1. Installs the display's OS-level Python dependencies.
2. Downloads the Waveshare GC9A01 driver.
3. Installs the GLaDOS files.
4. Installs the startup sound files.
5. Installs and enables the systemd services.
6. Starts the display service.

The default installation directory is:

~~~text
/opt/glados
~~~

Override it with "INSTALL_ROOT":

~~~bash
INSTALL_ROOT=/some/path ./scripts/install.sh
~~~

If the installer is run through sudo, the invoking user is used for the service account. To select the account explicitly:

~~~bash
GLADOS_USER=myuser ./scripts/install.sh
~~~

The display service runs as that user rather than requiring a particular username.

### Verify the installation

Check the display service:

~~~bash
sudo systemctl status glados-display.service
~~~

Follow its logs:

~~~bash
sudo journalctl -u glados-display.service -f
~~~

Check the startup sound services:

~~~bash
sudo systemctl status glados-powerup.service
sudo systemctl status glados-wakeup.service
~~~

## Configuration

The display process supports these environment variables:

| Variable | Default | Purpose |
|---|---|---|
| "LVA_WS_URL" | "ws://127.0.0.1:6055" | LVA peripheral WebSocket endpoint |
| "LVA_RECONNECT_DELAY" | "3" | Seconds between LVA reconnect attempts |
| "GLADOS_DISPLAY_FRAME_DURATION" | "0.25" | Animation frame duration |
| "GLADOS_SPI_FREQ" | "62500000" | SPI frequency in Hz |
| "LOG_LEVEL" | "INFO" | Python logging level |

The systemd service currently supplies the LVA endpoint. Change the service environment if a non-default endpoint is required.

## Display

The display renderer listens for LVA peripheral events and maps them to display states:

| LVA event | Display state |
|---|---|
| "wake_word_detected" | Wake |
| "listening" | Listening |
| "thinking" | Thinking |
| "tts_speaking" | Speaking |
| "tts_finished" | Idle |
| "idle" | Idle |
| "pipeline_error" | Error |
| "disconnected" | Connection error state |

The renderer automatically reconnects to LVA after a connection failure.

The GC9A01 is driven through a 240×240 window using 12-bit RGB444 transfers. The renderer calculates changed regions between display frames and only sends those regions over SPI when possible.

## Startup sounds

Two systemd services handle startup audio:

- "glados-powerup.service" plays the initial power-up sound once the audio device is available.
- "glados-wakeup.service" plays the remaining startup sequence after the system reaches the normal multi-user boot target.

The sound files are installed under:

~~~text
<INSTALL_ROOT>/sounds/
~~~

The services use ALSA "aplay" to play the installed WAV files.

## Logs

The installer configures systemd-journald with bounded retention:

- Maximum persistent journal size: 200 MB
- Keep at least 500 MB free
- Maximum runtime journal size: 100 MB
- Maximum journal age: 30 days

These limits apply to the system journal as a whole.

## Development

Create a development environment with [uv](https://docs.astral.sh/uv/):

~~~bash
uv sync --dev
~~~

Run the quality checks locally:

~~~bash
uv run ruff check .
uv run ruff format --check .
uv run ty check
~~~

Run the test suite and enforce the CI coverage requirement:

~~~bash
uv run pytest --cov=display --cov-report=term-missing --cov-fail-under=95
~~~

The same checks run automatically in GitHub Actions for pushes to main and pull requests.

The repository is intended to contain portable project configuration and installation logic. Machine-specific credentials, Docker volumes, generated wake-word files, local service state, and other host-specific data should not be committed.

## Repository layout

~~~text
GLaDOS/
├── .github/
│   └── workflows/
├── display/
│   ├── assets/
│   ├── driver.py
│   ├── glados_display.py
│   └── states.py
├── scripts/
│   ├── download-sounds.sh
│   ├── install-display.sh
│   ├── install-services.sh
│   └── install.sh
├── services/
│   ├── glados-display.service
│   ├── glados-powerup.service
│   └── glados-wakeup.service
├── sounds/
├── tests/
├── pyproject.toml
└── README.md
~~~

## Credits

This project builds on the work of **Mr. Volt (DJ Harrigan / @mr.v0lt)** and his GLaDOS project. The physical design and some hardware/component approaches were inspired by that work.

- [Mr. Volt YouTube](https://www.youtube.com/watch?v=W9VFbfcogbA)
- [Mr. Volt YouTube channel](https://www.youtube.com/c/MrVolt)
- [Mr. Volt Instagram](https://www.instagram.com/mr.v0lt/)

Please refer to the original project and its associated files for applicable licensing and attribution requirements.

## Third-party software

This project relies on external software and services, including:

- [Linux Voice Assistant](https://github.com/OHF-Voice/linux-voice-assistant)
- [Home Assistant](https://www.home-assistant.io/)
- The Waveshare GC9A01 Python driver
- Python, Pillow, NumPy, and websockets

Third-party projects retain their own licenses and attribution requirements. The MIT license in this repository applies to original material released by this project.

## License

This project is licensed under the [MIT License](LICENSE).
