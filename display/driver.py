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

        # Keep the full 240x240 update window for reliable GC9A01 refreshes.
        spi_freq = int(os.getenv("GLADOS_SPI_FREQ", "62500000"))
        self._lcd = LCD_1inch28.LCD_1inch28(spi_freq=spi_freq)
        self._frame_buffers = {}
        _LOGGER.info("LCD SPI frequency: %d Hz", spi_freq)
        self._lcd.Init()
        self._lcd.bl_DutyCycle(100)
        self._lcd.clear()

    def _rgb565(self, image):
        img = self._lcd.np.asarray(image)
        pix = self._lcd.np.zeros(
            (image.height, image.width, 2),
            dtype=self._lcd.np.uint8,
        )
        pix[..., [0]] = self._lcd.np.add(
            self._lcd.np.bitwise_and(img[..., [0]], 0xF8),
            self._lcd.np.right_shift(img[..., [1]], 5),
        )
        pix[..., [1]] = self._lcd.np.add(
            self._lcd.np.bitwise_and(self._lcd.np.left_shift(img[..., [1]], 3), 0xE0),
            self._lcd.np.right_shift(img[..., [2]], 3),
        )
        return pix.tobytes()

    def show(self, image):
        if image.size != (self.WIDTH, self.HEIGHT):
            raise ValueError("Display image must be exactly 240x240 pixels")

        start = time.monotonic()
        key = id(image)
        if key not in self._frame_buffers:
            self._frame_buffers[key] = self._rgb565(image)

        # Always program the complete 240x240 address window.  Partial
        # windows can leave stale pixels/white bars at the artwork edges.
        self._lcd.SetWindows(0, 0, self.WIDTH, self.HEIGHT)
        self._lcd.digital_write(self._lcd.DC_PIN, True)

        # xfer3() is intended for large SPI transfers and transparently
        # handles buffers larger than the kernel spidev bufsiz limit.
        self._lcd.SPI.xfer3(self._frame_buffers[key])

        elapsed = time.monotonic() - start
        _LOGGER.debug(
            "LCD full-frame transfer: %.1f ms (%d bytes)",
            elapsed * 1000,
            len(self._frame_buffers[key]),
        )

    def clear(self):
        self._lcd.clear()

    def close(self):
        self._lcd.clear()
        self._lcd.bl_DutyCycle(0)
