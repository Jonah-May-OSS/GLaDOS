"""GLaDOS display state renderer."""

import time
from typing import Optional
from PIL import Image, ImageDraw
try:
    from .driver import DisplayDriver
    from .states import DisplayState
except ImportError:
    from driver import DisplayDriver
    from states import DisplayState

SIZE = (240, 240)

class GladosDisplay:
    def __init__(self, driver: Optional[DisplayDriver] = None):
        self.driver = driver or DisplayDriver()
        self.state = None

    def render(self, state: DisplayState) -> None:
        image = Image.new("RGB", SIZE, "black")
        draw = ImageDraw.Draw(image)
        renderers = {
            DisplayState.IDLE: self._draw_idle,
            DisplayState.WAKE: self._draw_wake,
            DisplayState.LISTENING: self._draw_listening,
            DisplayState.THINKING: self._draw_thinking,
            DisplayState.SPEAKING: self._draw_speaking,
            DisplayState.ERROR: self._draw_error,
        }
        try:
            renderers[state](draw)
        except KeyError as exc:
            raise ValueError(f"Unsupported display state: {state}") from exc
        self.driver.show(image)
        self.state = state

    @staticmethod
    def _draw_idle(draw):
        draw.ellipse((72, 72, 168, 168), outline="white", width=4)
        draw.ellipse((104, 104, 136, 136), fill="white")

    @staticmethod
    def _draw_wake(draw):
        draw.ellipse((48, 48, 192, 192), outline="white", width=6)
        draw.ellipse((92, 92, 148, 148), fill="white")

    @staticmethod
    def _draw_listening(draw):
        draw.ellipse((58, 58, 182, 182), outline="white", width=5)
        draw.ellipse((100, 100, 140, 140), fill="white")

    @staticmethod
    def _draw_thinking(draw):
        draw.ellipse((70, 70, 170, 170), outline="white", width=4)
        for x in (100, 120, 140):
            draw.ellipse((x - 5, 115, x + 5, 125), fill="white")

    @staticmethod
    def _draw_speaking(draw):
        draw.ellipse((58, 58, 182, 182), outline="white", width=5)
        draw.arc((92, 92, 148, 148), 20, 160, fill="white", width=5)

    @staticmethod
    def _draw_error(draw):
        draw.ellipse((58, 58, 182, 182), outline="white", width=5)
        draw.line((92, 92, 148, 148), fill="white", width=7)
        draw.line((148, 92, 92, 148), fill="white", width=7)


def demo() -> None:
    display = GladosDisplay()
    sequence = list(DisplayState)
    try:
        while True:
            for state in sequence:
                print(f"display: {state.value}", flush=True)
                display.render(state)
                time.sleep(2)
    except KeyboardInterrupt:
        display.driver.clear()

if __name__ == "__main__":
    demo()
