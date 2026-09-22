# GLaDOS

A physical GLaDOS-inspired voice assistant head built around a Raspberry Pi 4, Home Assistant, and local voice-assistant infrastructure.

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

### Core

| Component | Status | Reference |
|---|---|---|
| Raspberry Pi 4 Model B | ✅ Installed | [Raspberry Pi](https://www.raspberrypi.com/products/raspberry-pi-4-model-b/) |
| MicroSD storage | ✅ Installed | — |
| USB-C power supply | ✅ Installed | — |

### Audio

| Component | Status | Reference |
|---|---|---|
| INNOTRIK USB Conference Microphone Speakerphone | ✅ Working | [Amazon](https://www.amazon.com/INNOTRIK-Conference-Microphone-Omnidirectional-Speakerphone/dp/B098DKS637) |

### Display

| Component | Status | Reference |
|---|---|---|
| Waveshare 1.28-inch LCD Module — SPI / GC9A01 / 240×240 IPS | ✅ Wired/tested | [Waveshare](https://www.waveshare.com/1.28inch-lcd-module.htm) |

### Motion

| Component | Status | Reference |
|---|---|---|
| Waveshare Servo Driver HAT | 🔧 Integration pending | [Waveshare](https://www.waveshare.com/product/robotics/drivers-sensors/servo-driver-hat.htm) |
| DSSERVO DS3225 25 kg digital servo | 🔧 Pending | [Amazon](https://www.amazon.com/dp/B07RNFQYD2) |
| DSSERVO DS3235 35 kg digital servo | 🔧 Pending | [Amazon](https://www.amazon.com/ZOSKAY-Coreless-Digital-Stainless-arduino/dp/B07S9XZYN2) |

The Servo Driver HAT and servos are part of the planned mechanical/animatronic system. Exact component links will be documented once the final hardware configuration is established.

### Lighting

| Component | Status | Reference |
|---|---|---|
| NeoPixel ring | 🔧 Integration pending | 16× 5050 addressable RGB LEDs |

The build uses a 16-LED ring with 5050 addressable RGB LEDs.

### Mechanical

- GLaDOS head/body components based on **Mr. Volt's** design
- 3D-printed components
- Additional mechanical hardware as required by the final assembly

### Current Hardware Status

| Component | Status |
|---|---|
| Raspberry Pi 4 | ✅ Installed |
| USB audio | ✅ Working |
| Linux Voice Assistant | ✅ Working |
| Hey GLaDOS wake word | ✅ Working |
| Home Assistant Assist | ✅ Working |
| GC9A01 display | ✅ Wired/tested |
| GLaDOS display software | 🚧 In development |
| Servo Driver HAT | 🔧 Integration pending |
| Servos | 🔧 Integration pending |
| NeoPixel ring | 🔧 Integration pending |


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

## Software & AI Components

The GLaDOS voice pipeline is built from several open-source projects and model ecosystems:

- **[wyoming-glados](https://github.com/nalf3in/wyoming-glados)** — Wyoming protocol server used to expose the GLaDOS TTS engine to Home Assistant. It is based on the GLaDOS TTS engine from R2D2FISH and is MIT licensed.
- **[wyoming-whisper-trt](https://github.com/JonahMMay/wyoming-whisper-trt)** — Wyoming-compatible OpenAI Whisper STT server accelerated with NVIDIA TensorRT. This project is maintained separately by Jonah May.
- **[llama.cpp](https://github.com/ggml-org/llama.cpp)** — Local LLM inference engine providing the OpenAI-compatible inference endpoint used by the Home Assistant voice pipeline. llama.cpp is MIT licensed.
- **[Local OpenAI LLM](https://github.com/skye-harris/hass_local_openai_llm)** — Home Assistant custom integration used to connect Assist to the local OpenAI-compatible llama.cpp server.
- **Gemma 4 E4B IT QAT** — The local language model used with llama.cpp and the Local OpenAI LLM integration. Gemma models are subject to Google's Gemma Terms of Use; the project license does not apply to the model weights.

These dependencies are external projects and retain their own licenses and attribution requirements. The MIT license in this repository applies only to original GLaDOS project code and other material that we own and choose to release under that license. Third-party files, models, designs, and other contributed material remain subject to their respective licenses.

## Development

This project is being developed incrementally on a Raspberry Pi 4 running Debian.

The goal is to keep the installation reproducible so the physical GLaDOS head can be rebuilt without relying on undocumented manual setup steps.

As components move from experimentation into the stable configuration, their installation and configuration should be represented in this repository.

## License

This project is licensed under the [MIT License](LICENSE).