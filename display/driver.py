"""Hardware adapter for the Waveshare 1.28-inch GC9A01 display."""

from pathlib import Path
import logging
import sys
import time

from PIL import ImageChops

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
        self._last_image = None

    def show(self, image):
        if image.size != (self.WIDTH, self.HEIGHT):
            raise ValueError("Display image must be exactly 240x240 pixels")

        if self._last_image is None:
            bbox = (0, 0, self.WIDTH, self.HEIGHT)
        else:
            bbox = ImageChops.difference(self._last_image, image).getbbox()
            if bbox is None:
                return

        start = time.monotonic()
        self._show_region(image, bbox)
        self._last_image = image.copy()
        elapsed = time.monotonic() - start
        pixels = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
        _LOGGER.debug(
            "LCD region transfer: %.1f ms (%dx%d, %d pixels)",
            elapsed * 1000,
            bbox[2] - bbox[0],
            bbox[3] - bbox[1],
            pixels,
        )

    def _show_region(self, image, bbox):
        """Write only the changed rectangular region to the LCD."""
        x0, y0, x1, y1 = bbox
        region = image.crop(bbox)
        img = self._lcd.np.asarray(region)
        width = x1 - x0
        height = y1 - y0

        pix = self._lcd.np.zeros((width, height, 2), dtype=self._lcd.np.uint8)
        pix[..., [0]] = self._lcd.np.add(
            self._lcd.np.bitwise_and(img[..., [0]], 0xF8),
            self._lcd.np.right_shift(img[..., [1]], 5),
        )
        pix[..., [1]] = self._lcd.np.add(
            self._lcd.np.bitwise_and(self._lcd.np.left_shift(img[..., [1]], 3), 0xE0),
            self._lcd.np.right_shift(img[..., [2]], 3),
        )
        pix = pix.flatten().tolist()

        self._lcd.SetWindows(x0, y0, x1, y1)
        self._lcd.digital_write(self._lcd.DC_PIN, True)
        for i in range(0, len(pix), 4096):
            self._lcd.spi_writebyte(pix[i:i + 4096])

    def clear(self):
        self._lcd.clear()
        self._last_image = None

    def close(self):
        self._lcd.clear()
        self._lcd.bl_DutyCycle(0)
        self._last_image = None
