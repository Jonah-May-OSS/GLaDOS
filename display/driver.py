"""Hardware adapter for the Waveshare 1.28-inch GC9A01 display."""

from pathlib import Path
import logging
import sys
import time
import os

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
        spi_freq = int(os.getenv("GLADOS_SPI_FREQ", "40000000"))
        self._lcd = LCD_1inch28.LCD_1inch28(spi_freq=spi_freq)
        self._frame_buffers = {}
        self._previous_image = None
        self._content_bbox = None
        _LOGGER.info("LCD SPI frequency: %d Hz", spi_freq)
        self._lcd.Init()
        self._lcd.bl_DutyCycle(100)
        self._lcd.clear()

    def _rgb565(self, image):
        img = self._lcd.np.asarray(image)
        pix = self._lcd.np.zeros((image.height, image.width, 2), dtype=self._lcd.np.uint8)
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

        if self._previous_image is None:
            dirty = image.getbbox()
            if dirty is None:
                dirty = (0, 0, self.WIDTH, self.HEIGHT)
            self._content_bbox = dirty
        else:
            # The diff bbox is the minimal rectangle containing pixels that
            # changed between the previous and current frame.
            dirty = ImageChops.difference(self._previous_image, image).getbbox()
            if dirty is None:
                _LOGGER.debug("LCD frame unchanged; skipping transfer")
                self._previous_image = image.copy()
                return

            # Keep the update inside the established artwork bounds.
            if self._content_bbox is not None:
                left = max(dirty[0], self._content_bbox[0])
                top = max(dirty[1], self._content_bbox[1])
                right = min(dirty[2], self._content_bbox[2])
                bottom = min(dirty[3], self._content_bbox[3])
                dirty = (left, top, right, bottom)

        left, top, right, bottom = dirty
        crop = image.crop(dirty)
        key = (id(image), dirty)
        if key not in self._frame_buffers:
            self._frame_buffers[key] = self._rgb565(crop)
            _LOGGER.debug(
                "Cached RGB565 dirty region for image id %d: %dx%d (%d bytes)",
                key,
                right - left,
                bottom - top,
                len(self._frame_buffers[key]),
            )

        self._lcd.SetWindows(left, top, right, bottom)
        self._lcd.digital_write(self._lcd.DC_PIN, True)
        pix = self._frame_buffers[key]
        self._lcd.SPI.writebytes2(pix)

        self._previous_image = image.copy()

        elapsed = time.monotonic() - start
        _LOGGER.debug(
            "LCD dirty transfer: %.1f ms (%dx%d, %d bytes)",
            elapsed * 1000,
            right - left,
            bottom - top,
            len(pix),
        )

    def clear(self):
        self._lcd.clear()
        self._previous_image = None
        self._content_bbox = None

    def close(self):
        self._lcd.clear()
        self._lcd.bl_DutyCycle(0)
