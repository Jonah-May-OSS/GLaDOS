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

The display has been verified using the official Waveshare Python driver and example. The Waveshare driver is hardware-specific and should remain separated from higher-level GLaDOS display and animation logic.

Planned display states:

- Idle
- Wake
- Listening
- Thinking
- Speaking
- Error

The display will eventually receive voice-assistant state from the Linux Voice Assistant peripheral interface rather than owning the voice-assistant pipeline itself.
