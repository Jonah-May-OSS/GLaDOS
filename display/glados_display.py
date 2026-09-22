"""GLaDOS display renderer using the supplied aperture artwork."""

import time
from pathlib import Path
from typing import Optional

from PIL import Image

try:
    from .driver import DisplayDriver
    from .states import DisplayState
except ImportError:
    from driver import DisplayDriver
    from states import DisplayState

SIZE = (240, 240)
SPRITE_PATH = Path(__file__).resolve().parent / "assets" / "aperture_sprite.png"
FRAME_COUNT = 9
APERTURE_COLOR = (255, 214, 0)


class GladosDisplay:
    def __init__(self, driver: Optional[DisplayDriver] = None):
        self.driver = driver or DisplayDriver()
        self.state = None

    @staticmethod
    def _load_frame(index: int) -> Image.Image:
        with Image.open(SPRITE_PATH) as sprite:
            top = (index % FRAME_COUNT) * SIZE[1]
            frame = sprite.crop((0, top, SIZE[0], top + SIZE[1])).convert("L")
        # Aperture.h is a 1-bit bitmap, so it contains shape information but
        # no color. Render the source-derived white pixels in GLaDOS yellow.
        mask = frame.point(lambda pixel: 255 if pixel else 0)
        image = Image.new("RGB", SIZE, (0, 0, 0))
        image.paste(APERTURE_COLOR, mask=mask)
        return image

    def render(self, state: DisplayState, frame: int = 0) -> None:
        # Aperture.h contains one complete aperture plus eight individual
        # blade masks. The sprite contains composites generated from those
        # exact source masks, so every frame is a real source-derived image.
        sequences = {
            DisplayState.IDLE: (0,),
            DisplayState.WAKE: (0, 1, 2, 3, 4, 5, 6, 7, 8),
            DisplayState.LISTENING: (8, 7, 6, 5, 4, 3, 2, 1, 0),
            DisplayState.THINKING: (0, 2, 4, 6, 8, 7, 5, 3, 1),
            DisplayState.SPEAKING: (1, 2, 3, 4, 5, 6, 7, 8, 0),
            DisplayState.ERROR: (0,),
        }
        sequence = sequences[state]
        image = self._load_frame(sequence[frame % len(sequence)])
        self.driver.show(image)
        self.state = state

    def animate(self, state: DisplayState, fps: float = 12.0, cycles: int = 1) -> None:
        sequences = {
            DisplayState.WAKE: (0, 1, 2, 3, 4, 5, 6, 7, 8),
            DisplayState.LISTENING: (8, 7, 6, 5, 4, 3, 2, 1, 0),
            DisplayState.THINKING: (0, 2, 4, 6, 8, 7, 5, 3, 1),
            DisplayState.SPEAKING: (1, 2, 3, 4, 5, 6, 7, 8, 0),
        }
        sequence = sequences.get(state, (0,))
        delay = 1.0 / max(fps, 1.0)

        for _ in range(cycles):
            for frame, _ in enumerate(sequence):
                self.render(state, frame)
                time.sleep(delay)


def demo() -> None:
    display = GladosDisplay()

    try:
        while True:
            print("display: idle", flush=True)
            display.render(DisplayState.IDLE)
            time.sleep(1.5)

            print("display: wake", flush=True)
            display.animate(DisplayState.WAKE, fps=12, cycles=1)

            print("display: listening", flush=True)
            display.animate(DisplayState.LISTENING, fps=12, cycles=2)

            print("display: thinking", flush=True)
            display.animate(DisplayState.THINKING, fps=12, cycles=2)

            print("display: speaking", flush=True)
            display.animate(DisplayState.SPEAKING, fps=12, cycles=2)

    except KeyboardInterrupt:
        display.driver.clear()


if __name__ == "__main__":
    demo()
