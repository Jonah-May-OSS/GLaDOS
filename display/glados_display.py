"""GLaDOS display renderer and LVA peripheral controller."""

import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Optional

from PIL import Image
import websockets

try:
    from .driver import DisplayDriver
    from .states import DisplayState
except ImportError:
    from driver import DisplayDriver
    from states import DisplayState

_LOGGER = logging.getLogger("glados.display")

SIZE = (240, 240)
SPRITE_PATH = Path(__file__).resolve().parent / "assets" / "aperture_sprite.png"
FRAME_COUNT = 9
APERTURE_COLOR = (255, 214, 0)
DISPLAY_X_OFFSET = -5

LVA_WS_URL = os.getenv("LVA_WS_URL", "ws://127.0.0.1:6055")
RECONNECT_DELAY = float(os.getenv("LVA_RECONNECT_DELAY", "3"))
FPS = float(os.getenv("GLADOS_DISPLAY_FPS", "12"))
FRAME_DURATION = float(os.getenv("GLADOS_DISPLAY_FRAME_DURATION", "0.25"))
LOOP_HEARTBEAT_INTERVAL = 0.1
LOOP_HEARTBEAT_WARN = 0.25

SEQUENCES = {
    DisplayState.IDLE: (0,),
    DisplayState.WAKE: (0, 1, 2, 3, 4, 5, 6, 7, 8),
    DisplayState.LISTENING: (8, 7, 6, 5, 4, 3, 2, 1, 0),
    DisplayState.THINKING: (0, 2, 4, 6, 8, 7, 5, 3, 1),
    DisplayState.SPEAKING: (1, 2, 3, 4, 5, 6, 7, 8, 7, 6, 5, 4, 3, 2),
}

ACTIVE_STATES = {
    "wake_word_detected": DisplayState.WAKE,
    "listening": DisplayState.LISTENING,
    "thinking": DisplayState.THINKING,
    "tts_speaking": DisplayState.SPEAKING,
    "idle": DisplayState.IDLE,
    "tts_finished": DisplayState.IDLE,
}


class GladosDisplay:
    """Render the GLaDOS aperture and follow LVA voice-assistant events."""

    def __init__(self, driver: Optional[DisplayDriver] = None):
        self.driver = driver or DisplayDriver()
        self.frames = self._load_frames()
        self.state = DisplayState.IDLE
        self.state_started = time.monotonic()
        self.connection_lost = False
        self._last_frame_key = None

    @staticmethod
    def _load_frames() -> list[Image.Image]:
        frames = []
        with Image.open(SPRITE_PATH) as sprite:
            for index in range(FRAME_COUNT):
                top = index * SIZE[1]
                mask = sprite.crop((0, top, SIZE[0], top + SIZE[1])).convert("L")
                shifted_mask = Image.new("L", SIZE, 0)
                shifted_mask.paste(mask, (DISPLAY_X_OFFSET, 0))
                image = Image.new("RGB", SIZE, (0, 0, 0))
                image.paste(APERTURE_COLOR, mask=shifted_mask)
                frames.append(image)
        return frames

    def set_state(self, state: DisplayState) -> None:
        if state != self.state:
            _LOGGER.info("Display state: %s -> %s", self.state.value, state.value)
            self.state = state
            self.state_started = time.monotonic()
            self._last_frame_key = None

    def _show_frame(self, frame_index: int) -> None:
        key = (frame_index, self.state)
        if key == self._last_frame_key:
            return
        _LOGGER.debug("Rendering frame %d in state %s", frame_index, self.state.value)
        self.driver.show(self.frames[frame_index])
        self._last_frame_key = key

    def _render_error(self, now: float) -> None:
        if self.connection_lost:
            phase = int((now - self.state_started) * 2) % 2
            if phase == 0:
                self._show_frame(8)
            else:
                self.driver.clear()
                self._last_frame_key = None
            return

        elapsed = now - self.state_started
        if elapsed >= 1.5:
            self.set_state(DisplayState.IDLE)
            self._show_frame(0)
            return

        phase = int(elapsed / 0.25)
        if phase % 2 == 0:
            self._show_frame(0)
        else:
            self.driver.clear()
            self._last_frame_key = None

    def render(self, now: Optional[float] = None) -> None:
        now = now if now is not None else time.monotonic()
        if self.state == DisplayState.ERROR:
            self._render_error(now)
            return
        sequence = SEQUENCES[self.state]
        elapsed = max(0.0, now - self.state_started)
        frame = min(int(elapsed / FRAME_DURATION), len(sequence) - 1)
        if self.state != DisplayState.WAKE:
            frame %= len(sequence)
        self._show_frame(sequence[frame])

    def handle_event(self, event: str, data: dict) -> None:
        if event == "snapshot":
            if data.get("ha_connected", True):
                self.connection_lost = False
                self.set_state(DisplayState.IDLE)
            else:
                self.connection_lost = True
                self.set_state(DisplayState.ERROR)
            return
        if event == "disconnected":
            self.connection_lost = True
            self.set_state(DisplayState.ERROR)
            return
        if event == "zeroconf":
            if data.get("status") == "connected":
                self.connection_lost = False
                self.set_state(DisplayState.IDLE)
            return
        if event == "pipeline_error":
            self.connection_lost = False
            self.set_state(DisplayState.ERROR)
            return
        if event in ACTIVE_STATES:
            self.connection_lost = False
            self.set_state(ACTIVE_STATES[event])

    async def _event_loop_heartbeat(self) -> None:
        """Detect long periods where this asyncio event loop cannot run."""
        expected = time.monotonic()
        while True:
            await asyncio.sleep(LOOP_HEARTBEAT_INTERVAL)
            now = time.monotonic()
            lag = now - expected - LOOP_HEARTBEAT_INTERVAL
            if lag >= LOOP_HEARTBEAT_WARN:
                _LOGGER.warning(
                    "EVENT LOOP STALL: %.3f s (state=%s)",
                    lag,
                    self.state.value,
                )
            expected = now

    async def _render_loop(self) -> None:
        """Render whenever the animation frame is due."""
        try:
            while True:
                loop_started = time.monotonic()
                now = loop_started
                _LOGGER.debug("Render loop: tick")
                self.render(now)
                render_finished = time.monotonic()

                if self.state == DisplayState.ERROR:
                    delay = 0.05
                else:
                    sequence = SEQUENCES[self.state]
                    elapsed = max(0.0, now - self.state_started)
                    frame = int(elapsed / FRAME_DURATION)
                    if self.state == DisplayState.WAKE:
                        frame = min(frame, len(sequence) - 1)
                    else:
                        frame %= len(sequence)
                    next_frame_time = self.state_started + (frame + 1) * FRAME_DURATION
                    delay = max(0.001, next_frame_time - time.monotonic())

                before_sleep = time.monotonic()
                _LOGGER.debug(
                    "Render loop: sleep %.3f s (render %.1f ms)",
                    delay,
                    (render_finished - loop_started) * 1000,
                )
                await asyncio.sleep(delay)

                woke = time.monotonic()
                render_time = render_finished - loop_started
                scheduler_lag = woke - before_sleep - delay
                if render_time > 0.1:
                    _LOGGER.warning(
                        "Render call took %.3f s (state=%s)",
                        render_time,
                        self.state.value,
                    )
                if scheduler_lag > 0.05:
                    _LOGGER.warning(
                        "Render loop wake lag %.3f s (requested sleep %.3f s, state=%s)",
                        scheduler_lag,
                        delay,
                        self.state.value,
                    )
        except asyncio.CancelledError:
            raise
        except Exception:
            _LOGGER.exception("Display render loop crashed")
            raise

    async def run(self) -> None:
        render_task = asyncio.create_task(self._render_loop())
        heartbeat_task = asyncio.create_task(self._event_loop_heartbeat())
        try:
            while True:
                try:
                    _LOGGER.info("Connecting to LVA peripheral API at %s", LVA_WS_URL)
                    async with websockets.connect(
                        LVA_WS_URL,
                        ping_interval=20,
                        ping_timeout=10,
                    ) as ws:
                        _LOGGER.info("Connected to LVA peripheral API")
                        self.connection_lost = False
                        async for raw in ws:
                            try:
                                message = json.loads(raw)
                            except json.JSONDecodeError:
                                _LOGGER.warning("Ignoring invalid LVA message: %r", raw)
                                continue
                            event = message.get("event", "")
                            data = message.get("data") or {}
                            if event:
                                _LOGGER.debug("LVA event: %s %s", event, data)
                                self.handle_event(event, data)
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    self.connection_lost = True
                    self.set_state(DisplayState.ERROR)
                    _LOGGER.warning(
                        "LVA connection lost (%s); retrying in %.1fs",
                        exc,
                        RECONNECT_DELAY,
                    )
                    await asyncio.sleep(RECONNECT_DELAY)
        finally:
            render_task.cancel()
            heartbeat_task.cancel()
            await asyncio.gather(render_task, heartbeat_task, return_exceptions=True)
            self.close()

    def close(self) -> None:
        try:
            self.driver.close()
        except Exception:
            _LOGGER.exception("Error while closing display")


async def main() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    display = GladosDisplay()
    await display.run()


def demo() -> None:
    display = GladosDisplay()
    try:
        while True:
            display.set_state(DisplayState.IDLE)
            display.render()
            time.sleep(1.5)
            for state in (DisplayState.WAKE, DisplayState.LISTENING, DisplayState.THINKING, DisplayState.SPEAKING):
                display.set_state(state)
                start = time.monotonic()
                duration = len(SEQUENCES[state]) / FPS
                while time.monotonic() - start < duration:
                    display.render()
                    time.sleep(1 / max(FPS, 1.0))
    except KeyboardInterrupt:
        pass
    finally:
        display.close()


if __name__ == "__main__":
    asyncio.run(main())
