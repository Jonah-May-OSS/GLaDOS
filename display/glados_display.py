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
ASSET_DIR = Path(__file__).resolve().parent / "assets"
APERTURE_FRAMES = tuple(
    ASSET_DIR / f"aperture{index}.png" for index in range(9)
)


class GladosDisplay:
    def __init__(self, driver: Optional[DisplayDriver] = None):
        self.driver = driver or DisplayDriver()
        self.state = None

    @staticmethod
    def _load_frame(index: int) -> Image.Image:
        path = APERTURE_FRAMES[index % len(APERTURE_FRAMES)]
        with Image.open(path) as source:
            return source.convert("RGB")

    def render(self, state: DisplayState, frame: int = 0) -> None:
        sequences = {
            DisplayState.IDLE: (0,),
            DisplayState.WAKE: (0,),
            DisplayState.LISTENING: (1, 2, 3, 4, 5, 6, 7, 8),
            DisplayState.THINKING: (8, 7, 6, 5, 4, 3, 2, 1),
            DisplayState.SPEAKING: (0, 1, 2, 3, 4, 5, 6, 7, 8),
            DisplayState.ERROR: (0,),
        }
        try:
            sequence = sequences[state]
        except KeyError as exc:
            raise ValueError(f"Unsupported display state: {state}") from exc

        image = self._load_frame(sequence[frame % len(sequence)])
        self.driver.show(image)
        self.state = state

    def animate(self, state: DisplayState, fps: float = 12.0, cycles: int = 1) -> None:
        """Play the aperture sequence for a state."""
        sequences = {
            DisplayState.LISTENING: (1, 2, 3, 4, 5, 6, 7, 8),
            DisplayState.THINKING: (8, 7, 6, 5, 4, 3, 2, 1),
            DisplayState.SPEAKING: (0, 1, 2, 3, 4, 5, 6, 7, 8),
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
            display.render(DisplayState.WAKE)
            time.sleep(0.5)

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
