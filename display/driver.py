"""Hardware adapter for the Waveshare 1.28-inch GC9A01 display."""

from pathlib import Path
import logging
import sys
import time

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
        self._lcd = LCD_1inch28.LCD_1inch28()
        self._lcd.Init()
        self._lcd.bl_DutyCycle(100)
        self._lcd.clear()

    def show(self, image):
        if image.size != (self.WIDTH, self.HEIGHT):
            raise ValueError("Display image must be exactly 240x240 pixels")
        start = time.monotonic()
        self._lcd.ShowImage(image)
        elapsed = time.monotonic() - start
        _LOGGER.debug("LCD frame transfer: %.1f ms", elapsed * 1000)

    def clear(self):
        self._lcd.clear()

    def close(self):
        self._lcd.clear()
        self._lcd.bl_DutyCycle(0)
