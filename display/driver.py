"""Hardware adapter for the Waveshare 1.28-inch GC9A01 display."""

from pathlib import Path
import logging
import sys
import time
import os

WAVESHARE_DRIVER_DIR = Path("/opt/glados/display/waveshare")
_LOGGER = logging.getLogger("glados.display.driver")


class DisplayDriver:
    """Small hardware-neutral wrapper around Waveshare's LCD_1inch28 driver."""
    WIDTH = 240
    HEIGHT = 240

    def __init__(self):
        sys.path.insert(0, str(WAVESHARE_DRIVER_DIR))
        try:
            from lib import LCD_1inch28
        except ImportError as exc:
            raise RuntimeError("Waveshare driver not installed. Run scripts/install-display.sh first.") from exc
        spi_freq = int(os.getenv("GLADOS_SPI_FREQ", "40000000"))
        self._lcd = LCD_1inch28.LCD_1inch28(spi_freq=spi_freq)
        self._frame_buffers = {}
        _LOGGER.info("LCD SPI frequency: %d Hz", spi_freq)
        self._lcd.Init()
        self._lcd.bl_DutyCycle(100)
        self._lcd.clear()

    def show(self, image):
        if image.size != (self.WIDTH, self.HEIGHT):
            raise ValueError("Display image must be exactly 240x240 pixels")
        start = time.monotonic()
        key = id(image)
        if key not in self._frame_buffers:
            img = self._lcd.np.asarray(image)
            pix = self._lcd.np.zeros((self.WIDTH, self.HEIGHT, 2), dtype=self._lcd.np.uint8)
            pix[..., [0]] = self._lcd.np.add(
                self._lcd.np.bitwise_and(img[..., [0]], 0xF8),
                self._lcd.np.right_shift(img[..., [1]], 5),
            )
            pix[..., [1]] = self._lcd.np.add(
                self._lcd.np.bitwise_and(self._lcd.np.left_shift(img[..., [1]], 3), 0xE0),
                self._lcd.np.right_shift(img[..., [2]], 3),
            )
            self._frame_buffers[key] = pix.tobytes()
            _LOGGER.debug("Cached RGB565 frame buffer for image id %d", key)

        self._lcd.SetWindows(0, 0, self.WIDTH, self.HEIGHT)
        self._lcd.digital_write(self._lcd.DC_PIN, True)
        pix = self._frame_buffers[key]
        chunk_timings = []
        for i in range(0, len(pix), 4096):
            chunk_start = time.monotonic()
            self._lcd.SPI.writebytes2(pix[i:i + 4096])
            chunk_elapsed = time.monotonic() - chunk_start
            chunk_timings.append(chunk_elapsed * 1000)

        slow_chunks = [
            (index, elapsed)
            for index, elapsed in enumerate(chunk_timings)
            if elapsed > 2.0
        ]
        if slow_chunks:
            _LOGGER.debug(
                "Slow LCD SPI chunks: %s",
                ", ".join(f"#{index}={elapsed:.1f} ms" for index, elapsed in slow_chunks),
            )
        elapsed = time.monotonic() - start
        _LOGGER.debug("LCD frame transfer: %.1f ms", elapsed * 1000)

    def clear(self):
        self._lcd.clear()

    def close(self):
        self._lcd.clear()
        self._lcd.bl_DutyCycle(0)
