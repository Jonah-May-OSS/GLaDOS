"""Hardware adapter for the Waveshare 1.28-inch GC9A01 display."""

from pathlib import Path
import logging
import sys
import time
import os

WAVESHARE_DRIVER_DIR = Path("/opt/glados/display/waveshare")
_LOGGER = logging.getLogger("glados.display.driver")


class DisplayDriver:
    """Small hardware-neutral wrapper around Waveshare's GC9A01 display."""
    WIDTH = 240
    HEIGHT = 240

    def __init__(self):
        sys.path.insert(0, str(WAVESHARE_DRIVER_DIR))
        try:
            from lib import LCD_1inch28
        except ImportError as exc:
            raise RuntimeError("Waveshare driver not installed. Run scripts/install-display.sh first.") from exc

        # Keep the full 240x240 update window for reliable GC9A01 refreshes.
        # Use 12-bit MCU pixel mode to reduce each framebuffer by 25%.
        spi_freq = int(os.getenv("GLADOS_SPI_FREQ", "62500000"))
        self._lcd = LCD_1inch28.LCD_1inch28(spi_freq=spi_freq)
        self._frame_buffers = {}
        _LOGGER.info("LCD SPI frequency: %d Hz", spi_freq)
        self._lcd.Init()
        self._lcd.bl_DutyCycle(100)

        # COLMOD: 12-bit/pixel MCU interface.
        self._lcd.command(0x3A)
        self._lcd.data(0x03)
        self._lcd.clear()

    def _rgb444(self, image):
        """Pack two RGB444 pixels into three bytes for GC9A01 12-bit mode."""
        img = self._lcd.np.asarray(image)
        r = self._lcd.np.right_shift(img[..., 0], 4)
        g = self._lcd.np.right_shift(img[..., 1], 4)
        b = self._lcd.np.right_shift(img[..., 2], 4)

        pixels = (r.astype(self._lcd.np.uint16) << 8) | (g.astype(self._lcd.np.uint16) << 4) | b
        pixels = pixels.reshape(-1)

        if pixels.size % 2:
            pixels = self._lcd.np.append(pixels, 0)

        packed = self._lcd.np.empty((pixels.size // 2, 3), dtype=self._lcd.np.uint8)
        p0 = pixels[0::2]
        p1 = pixels[1::2]
        packed[:, 0] = self._lcd.np.right_shift(p0, 4)
        packed[:, 1] = self._lcd.np.bitwise_or(
            self._lcd.np.left_shift(self._lcd.np.bitwise_and(p0, 0x0F), 4),
            self._lcd.np.right_shift(p1, 8),
        )
        packed[:, 2] = self._lcd.np.bitwise_and(p1, 0xFF)
        return packed.tobytes()

    def show(self, image):
        if image.size != (self.WIDTH, self.HEIGHT):
            raise ValueError("Display image must be exactly 240x240 pixels")

        start = time.monotonic()
        pixels = self._lcd.np.asarray(image)

        # Only transmit pixels that changed since the previous frame.
        # The first frame is necessarily a full-frame update.
        if not hasattr(self, "_last_pixels"):
            x0, y0, x1, y1 = 0, 0, self.WIDTH, self.HEIGHT
        else:
            changed = self._lcd.np.any(pixels != self._last_pixels, axis=2)
            ys, xs = self._lcd.np.nonzero(changed)
            if len(xs) == 0:
                return

            x0, x1 = int(xs.min()), int(xs.max()) + 1
            y0, y1 = int(ys.min()), int(ys.max()) + 1

            # RGB444 packs two pixels into three bytes. Keep the rectangle
            # at an even pixel count so the transfer ends cleanly.
            if ((x1 - x0) * (y1 - y0)) & 1:
                if x1 < self.WIDTH:
                    x1 += 1
                elif x0 > 0:
                    x0 -= 1
                else:
                    y1 += 1

        crop = image.crop((x0, y0, x1, y1))
        buffer = self._rgb444(crop)

        self._lcd.SetWindows(x0, y0, x1, y1)
        self._lcd.digital_write(self._lcd.DC_PIN, True)
        self._lcd.SPI.writebytes2(buffer)
        self._last_pixels = pixels.copy()

        elapsed = time.monotonic() - start
        _LOGGER.debug(
            "LCD RGB444 changed-region transfer: %.1f ms (%d bytes, %dx%d at %d,%d)",
            elapsed * 1000,
            len(buffer),
            x1 - x0,
            y1 - y0,
            x0,
            y0,
        )

    def clear(self):
        self._lcd.clear()

    def close(self):
        self._lcd.clear()
        self._lcd.bl_DutyCycle(0)
