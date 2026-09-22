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
  ├─ Local MicroWakeWord
  └─ Peripheral WebSocket API
       │
       ├──────────────► GLaDOS Display
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
| Raspberry Pi 4 Model B | ✅ Installed | [Amazon](https://www.amazon.com/s?k=Raspberry+Pi+4+Model+B) |
| MicroSD storage | ✅ Installed | — |
| USB-C power supply | ✅ Installed | — |

### Audio

| Component | Status | Reference |
|---|---|---|
| INNOTRIK USB Conference Microphone Speakerphone | ✅ Working | [Amazon](https://www.amazon.com/INNOTRIK-Conference-Microphone-Omnidirectional-Speakerphone/dp/B098DKS637) |

### Display

| Component | Status | Reference |
|---|---|---|
| Waveshare 1.28-inch LCD Module — SPI / GC9A01 / 240×240 IPS | ✅ Wired/tested | [Amazon](https://www.amazon.com/s?k=Waveshare+1.28inch+LCD+Module+GC9A01) |

### Motion

| Component | Status | Reference |
|---|---|---|
| Waveshare Servo Driver HAT | 🔧 Integration pending | [Waveshare](https://www.waveshare.com/product/robotics/drivers-sensors/servo-driver-hat.htm) |
| DSSERVO DS3225 25 kg digital servo | 🔧 Pending | [Amazon](https://www.amazon.com/dp/B07RNFQYD2) |
| DSSERVO DS3235 35 kg digital servo | 🔧 Pending | [Amazon](https://www.amazon.com/ZOSKAY-Coreless-Digital-Stainless-arduino/dp/B07S9XZYN2) |

### Lighting

| Component | Status | Reference |
|---|---|---|
| 16× 5050 addressable RGB LED ring | 🔧 Integration pending | [Amazon](https://www.amazon.com/s?k=16+LED+5050+RGB+NeoPixel+ring) |

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
| GLaDOS display software | 🚧 Integration complete; hardware/animation testing |
| Servo Driver HAT | 🔧 Integration pending |
| Servos | 🔧 Integration pending |
| NeoPixel ring | 🔧 Integration pending |



## Linux Voice Assistant (LVA) Setup

The Raspberry Pi runs [Linux Voice Assistant](https://github.com/OHF-Voice/linux-voice-assistant) in Docker. LVA provides:

- Local MicroWakeWord detection
- The ESPHome API used by Home Assistant
- The peripheral WebSocket API used by the GLaDOS display
- USB microphone/speaker access through the host PipeWire/PulseAudio socket

The GLaDOS display connects directly to LVA on **TCP/WebSocket port 6055**. Home Assistant does not need a separate API token for the display.

### Prerequisites

The Pi should have:

- Debian Linux on ARM64
- Docker Engine
- Docker Compose v2
- PipeWire and `pipewire-pulse`
- The USB microphone/speaker connected and working
- A persistent user runtime directory for PipeWire

Enable the user runtime to survive boot:

~~~bash
loginctl enable-linger administrator
~~~

Verify PipeWire/PulseAudio:

~~~bash
pactl info
~~~

The default sink and source should point to the USB audio device.

### Install LVA

Clone the upstream LVA project:

~~~bash
cd ~
git clone https://github.com/OHF-Voice/linux-voice-assistant.git
cd ~/linux-voice-assistant
cp .env.example .env
~~~

For the GLaDOS Pi, the important Docker environment is:

~~~dotenv
LVA_USER_ID="1000"
LVA_USER_GROUP="1000"
LVA_PULSE_SERVER="/run/user/${LVA_USER_ID}/pulse/native"
LVA_XDG_RUNTIME_DIR="/run/user/${LVA_USER_ID}"
LVA_PULSE_COOKIE="/run/user/${LVA_USER_ID}/pulse/cookie"
~~~

The upstream Docker Compose configuration uses host networking and provides the ESPHome API on port **6053** and the peripheral WebSocket API on port **6055** by default.

Start LVA:

~~~bash
docker compose up -d
~~~

Check it:

~~~bash
docker compose ps
docker logs -f linux-voice-assistant
~~~

Home Assistant should discover the LVA device through the ESPHome integration. Complete the Home Assistant Assist pipeline configuration before testing the physical GLaDOS head.

### Hey GLaDOS wake word

This build uses the custom **Hey GLaDOS** MicroWakeWord model from [TaterTotterson/microWakeWords](https://github.com/TaterTotterson/microWakeWords).

The model configuration is:

~~~yaml
micro_wake_word:
  id: mww
  models:
    - model: https://github.com/TaterTotterson/microWakeWords/raw/refs/heads/main/microWakeWords/hey_glados.json
      id: hey_glados
~~~

The current GLaDOS setup uses:

~~~dotenv
WAKE_WORD_DIR="app/wakewords/custom"
WAKE_MODEL="hey_glados"
~~~

The custom wake-word files are stored in the LVA Docker volume rather than committed to this repository. Do **not** put generated model files or machine-specific Docker volume contents in Git.

After changing the wake-word files or LVA configuration:

~~~bash
cd ~/linux-voice-assistant
docker compose restart linux-voice-assistant
~~~

### LVA peripheral API

LVA is the WebSocket server and hardware peripherals connect as clients:

~~~text
GLaDOS display
      │
      │ WebSocket
      ▼
ws://127.0.0.1:6055
      │
      ▼
Linux Voice Assistant
      │
      │ ESPHome API
      ▼
Home Assistant
~~~

The display listens for:

| LVA event | Display state |
|---|---|
| `wake_word_detected` | Aperture opening |
| `listening` | Listening animation |
| `thinking` | Thinking animation |
| `tts_speaking` | Speaking animation |
| `tts_finished` / `idle` | Idle |
| `pipeline_error` | Error flash |
| `disconnected` | Connection-lost pulse |

LVA sends a state snapshot immediately after the display connects, and the display automatically reconnects if LVA restarts.

For LVA's complete peripheral API documentation, see the [upstream peripheral API documentation](https://github.com/OHF-Voice/linux-voice-assistant/blob/main/docs/peripheral_api.md).

### Docker startup

LVA should be configured with:

~~~bash
docker compose up -d
~~~

and configured to restart automatically by the upstream Compose configuration.

The GLaDOS display is managed separately by systemd, so Docker and systemd can restart independently:

~~~text
Boot
 ├─ PipeWire
 ├─ Docker
 │   └─ Linux Voice Assistant
 │       └─ peripheral API :6055
 │
 └─ glados-display.service
     └─ connects/reconnects to LVA :6055
~~~

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

The boot sequence is managed by `services/glados-boot-sounds.service` and plays the three clips in order:

1. `powerup01.wav`
2. `powerup02.wav`
3. `glados_wakeup.wav`

The service waits for the USB audio device to appear before starting playback, then plays each clip sequentially. This avoids the two independent boot services racing each other or starting before the USB audio device is ready.

The installation scripts place the runtime files under:

```text
/opt/glados/
```

The display service connects to the Linux Voice Assistant peripheral WebSocket API on port 6055. This lets the display follow Home Assistant Assist state without a Home Assistant access token or a separate HA API connection.

### Install

From a clone of this repository:

```bash
cd ~/GLaDOS
git pull
./scripts/install.sh
```

The installation scripts are tracked as executable files in Git, so a normal checkout should not require `chmod +x`.

> **Raspberry Pi note:** Git can report executable-bit changes as local modifications when `core.filemode` is enabled and the checkout predates the executable-bit fix. On a dedicated Pi checkout, disable file-mode tracking once:
>
> ```bash
> git config core.filemode false
> ```
>
> This is a Git working-tree setting, not a `.gitignore` rule; `.gitignore` cannot ignore Unix permission changes.

The installer installs the display dependencies and Waveshare driver, copies the display software to `/opt/glados`, downloads the required sound files, installs/enables the systemd services, and starts the display service immediately.

To test the boot sequence manually without rebooting:

```bash
sudo systemctl start glados-boot-sounds.service
```

Check its log:

```bash
sudo journalctl -u glados-boot-sounds.service -n 50 --no-pager
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

The GLaDOS display service runs at boot and follows LVA events:

- Wake word → aperture opening
- Listening → listening animation
- Thinking → thinking animation
- Speaking → speaking animation
- Idle → idle aperture
- Pipeline error → brief error flash
- LVA/HA disconnected → connection-lost pulse

The service automatically reconnects if LVA restarts.

## Repository Layout

```text
GLaDOS/
├── README.md
├── services/
│   ├── glados-boot-sounds.service
│   └── glados-display.service
├── scripts/
│   ├── install.sh
│   ├── install-services.sh
│   ├── download-sounds.sh
│   └── install-display.sh
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