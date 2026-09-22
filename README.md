# GLaDOS

A physical GLaDOS-inspired voice assistant head built around a Raspberry Pi 4, Home Assistant, and local voice-assistant infrastructure.

> **Status:** Active development

## Overview

The GLaDOS head is the physical endpoint for a Home Assistant voice assistant. The Raspberry Pi handles the local hardware and audio endpoint while Home Assistant provides the voice-assistant pipeline.

Current architecture:

```text
USB Microphone
      │
      ▼
Linux Voice Assistant (LVA)
  └─ Local MicroWakeWord
       │
       │ ESPHome API
       ▼
Home Assistant
  └─ NVIDIA-backed Assist pipeline
       │
       ▼
USB Speaker
```

The Raspberry Pi is intentionally **not** responsible for local STT, LLM inference, or TTS. Those workloads remain on the Home Assistant infrastructure.

## Hardware

Current hardware includes:

- Raspberry Pi 4 Model B
- INNOTRIK USB PnP Sound Device
- Waveshare 1.28-inch LCD Module
  - 240×240 IPS
  - GC9A01 controller
  - SPI interface
- Servo Driver HAT
- DSSERVO digital servos
- NeoPixel ring

The display and servo hardware are being integrated incrementally.

## Voice Assistant

The Pi runs [Linux Voice Assistant](https://github.com/OHF-Voice/linux-voice-assistant) in Docker.

The current wake word is:

**Hey GLaDOS**

The custom MicroWakeWord model is based on the model published by Tater Totterson:

https://github.com/TaterTotterson/microWakeWords

The LVA container uses the `latest` image tag and is automatically updated daily by Watchtower. Watchtower is configured to update only the LVA container and clean up replaced images.

## Audio

PipeWire provides the audio session on the Raspberry Pi.

The USB sound device is used for both:

- Microphone input
- Speaker output

The system uses the user's PipeWire/PulseAudio runtime socket so LVA can access the same audio devices.

## Boot Sounds

The head currently plays a short startup sequence when the Pi boots:

1. Power-up sound
2. Second power-up sound
3. GLaDOS wake-up sound

The systemd units for these sounds are in:

```text
services/
```

The installation scripts place the runtime files under:

```text
/opt/glados/
```

### Install

From a clone of this repository:

```bash
./scripts/install.sh
```

The installer downloads the required sound files and installs/enables the systemd services.

To test the services manually:

```bash
sudo systemctl start glados-powerup.service
sudo systemctl start glados-wakeup.service
```

## Display

The Waveshare 1.28-inch LCD uses the GC9A01 controller over SPI.

Current wiring:

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

The display has been verified using the official Waveshare Python driver and example.

A dedicated GLaDOS display service is planned and will replace the demonstration clock.

Planned display states include:

- Idle
- Wake
- Listening
- Thinking
- Speaking
- Error

## Repository Layout

```text
GLaDOS/
├── README.md
├── services/
│   ├── glados-powerup.service
│   └── glados-wakeup.service
├── scripts/
│   ├── install.sh
│   ├── install-services.sh
│   └── download-sounds.sh
└── sounds/
```

Additional display, animation, configuration, and hardware-control components will be added as development continues.

## Credits

This project builds on the work of **Mr. Volt (DJ Harrigan / @mr.v0lt)** and his GLaDOS project.

We are using and adapting elements from his work, including STEP/3D design files, code, and hardware/component approaches. His original project was a major reference for the physical design and implementation of this build.

- YouTube: https://www.youtube.com/watch?v=W9VFbfcogbA
- YouTube channel: https://www.youtube.com/c/MrVolt
- Instagram: https://www.instagram.com/mr.v0lt/

Please refer to the original project and its associated files for the applicable licensing and attribution requirements. This repository does not claim ownership of Mr. Volt's original work.

## Development

This project is being developed incrementally on a Raspberry Pi 4 running Debian.

The goal is to keep the installation reproducible so the physical GLaDOS head can be rebuilt without relying on undocumented manual setup steps.

As components move from experimentation into the stable configuration, their installation and configuration should be represented in this repository.

## License

License has not yet been selected.