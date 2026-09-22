"""Unit tests for the GLaDOS display renderer and hardware adapter."""

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest
from PIL import Image

from display import driver as driver_module
from display.glados_display import (
    ACTIVE_STATES,
    FRAME_DURATION,
    GladosDisplay,
)
from display.states import DisplayState


class FakeDisplayDriver:
    def __init__(self):
        self.shown = []
        self.clears = 0
        self.closed = False

    def show(self, image):
        self.shown.append(image)

    def clear(self):
        self.clears += 1

    def close(self):
        self.closed = True


@pytest.fixture
def display():
    return GladosDisplay(FakeDisplayDriver())


def test_loads_all_frames(display):
    assert len(display.frames) == 9
    assert all(frame.size == (240, 240) for frame in display.frames)
    assert display.frames[0].mode == "RGB"


def test_state_changes_reset_animation(display, monkeypatch):
    monkeypatch.setattr("display.glados_display.time.monotonic", lambda: 10.0)
    display.set_state(DisplayState.SPEAKING)
    assert display.state == DisplayState.SPEAKING
    assert display.state_started == 10.0
    assert display._last_frame_key is None

    display.set_state(DisplayState.SPEAKING)
    assert display.state_started == 10.0


@pytest.mark.parametrize(
    ("state", "elapsed", "expected"),
    [
        (DisplayState.IDLE, 0.0, 0),
        (DisplayState.WAKE, FRAME_DURATION * 8.9, 8),
        (DisplayState.LISTENING, FRAME_DURATION * 1.1, 7),
        (DisplayState.THINKING, FRAME_DURATION * 2.1, 4),
        (DisplayState.SPEAKING, FRAME_DURATION * 9.1, 7),
    ],
)
def test_frame_at(display, state, elapsed, expected):
    display.state = state
    display.state_started = 100.0
    frame, next_due = display._frame_at(100.0 + elapsed)
    assert frame == expected
    assert next_due > 100.0 + elapsed


def test_show_frame_deduplicates(display):
    display._show_frame(0)
    display._show_frame(0)
    display._show_frame(1)
    assert len(display.driver.shown) == 2


@pytest.mark.parametrize(
    ("event", "expected"),
    [(event, state) for event, state in ACTIVE_STATES.items()],
)
def test_active_events(event, expected, display):
    display.handle_event(event, {})
    assert display.state == expected
    assert display.connection_lost is False


def test_snapshot_connection_states(display):
    display.handle_event("snapshot", {"ha_connected": False})
    assert display.state == DisplayState.ERROR
    assert display.connection_lost is True

    display.handle_event("snapshot", {"ha_connected": True})
    assert display.state == DisplayState.IDLE
    assert display.connection_lost is False


def test_misc_events(display):
    display.handle_event("disconnected", {})
    assert display.state == DisplayState.ERROR
    assert display.connection_lost is True

    display.handle_event("zeroconf", {"status": "connected"})
    assert display.state == DisplayState.IDLE
    assert display.connection_lost is False

    display.handle_event("pipeline_error", {})
    assert display.state == DisplayState.ERROR
    assert display.connection_lost is False

    previous = display.state
    display.handle_event("unknown", {})
    assert display.state == previous


def test_render_and_error_paths(display, monkeypatch):
    monkeypatch.setattr("display.glados_display.time.monotonic", lambda: 10.0)
    display.set_state(DisplayState.IDLE)
    display.render(10.0)
    assert len(display.driver.shown) == 1

    display.connection_lost = True
    display.set_state(DisplayState.ERROR)
    display.render(display.state_started)
    display.render(display.state_started + 0.5)
    assert display.driver.clears == 1

    display.connection_lost = False
    display.state_started = 20.0
    display.render(20.1)
    display.render(20.3)
    assert display.driver.clears == 2

    display.state_started = 18.0
    display.render(20.0)
    assert display.state == DisplayState.IDLE


@pytest.mark.asyncio
async def test_heartbeat_warns_on_lag(display, monkeypatch, caplog):
    sleeps = iter([None, asyncio.CancelledError()])
    expected = iter([10.0, 10.5])
    monkeypatch.setattr(
        "display.glados_display.time",
        SimpleNamespace(monotonic=lambda: next(expected)),
    )

    async def fake_sleep(_):
        value = next(sleeps)
        if isinstance(value, BaseException):
            raise value

    monkeypatch.setattr("display.glados_display.asyncio.sleep", fake_sleep)
    with pytest.raises(asyncio.CancelledError):
        await display._event_loop_heartbeat()
    assert "EVENT LOOP STALL" in caplog.text


def test_render_task_done_logs(display, caplog):
    cancelled = MagicMock()
    cancelled.cancelled.return_value = True
    display._render_task_done(cancelled)
    assert "cancelled" in caplog.text

    failed = MagicMock()
    failed.cancelled.return_value = False
    failed.exception.return_value = RuntimeError("boom")
    display._render_task_done(failed)
    assert "CRASHED" in caplog.text

    finished = MagicMock()
    finished.cancelled.return_value = False
    finished.exception.return_value = None
    display._render_task_done(finished)
    assert "exited unexpectedly" in caplog.text


@pytest.mark.asyncio
async def test_render_loop_can_be_cancelled(display):
    async def stop_sleep(_):
        raise asyncio.CancelledError

    display.render = MagicMock()
    original_sleep = asyncio.sleep
    try:
        asyncio.sleep = stop_sleep
        with pytest.raises(asyncio.CancelledError):
            await display._render_loop()
    finally:
        asyncio.sleep = original_sleep
    display.render.assert_called_once()


@pytest.mark.asyncio
async def test_run_handles_events_and_cancellation(display, monkeypatch):
    class FakeWebSocket:
        def __init__(self):
            self.messages = iter(
                [
                    json.dumps({"event": "snapshot", "data": {"ha_connected": True}}),
                    "{invalid",
                    json.dumps({"event": "listening", "data": {}}),
                ]
            )

        def __aiter__(self):
            return self

        async def __anext__(self):
            try:
                return next(self.messages)
            except StopIteration:
                raise StopAsyncIteration

    class FakeConnection:
        def __init__(self):
            self.ws = FakeWebSocket()

        async def __aenter__(self):
            return self.ws

        async def __aexit__(self, exc_type, exc, tb):
            return False

    connections = iter([FakeConnection(), asyncio.CancelledError()])

    def connect(*_args, **_kwargs):
        next_connection = next(connections)
        if isinstance(next_connection, BaseException):
            raise next_connection
        return next_connection

    async def idle_task():
        await asyncio.Event().wait()

    monkeypatch.setattr("display.glados_display.websockets.connect", connect)
    monkeypatch.setattr(display, "_render_loop", idle_task)
    monkeypatch.setattr(display, "_event_loop_heartbeat", idle_task)

    with pytest.raises(asyncio.CancelledError):
        await display.run()

    assert display.state == DisplayState.LISTENING
    assert display.driver.closed is True


@pytest.mark.asyncio
async def test_main(monkeypatch):
    instance = MagicMock()
    instance.run = AsyncMock()
    monkeypatch.setattr("display.glados_display.GladosDisplay", MagicMock(return_value=instance))
    from display.glados_display import main

    await main()
    instance.run.assert_awaited_once()


def test_driver_rgb444():
    driver = object.__new__(driver_module.DisplayDriver)
    driver._lcd = SimpleNamespace(np=np)
    image = Image.new("RGB", (2, 1), (255, 128, 16))
    assert driver._rgb444(image) == bytes([0xF8, 0x1F, 0x81])


def test_driver_rgb444_odd_pixels():
    driver = object.__new__(driver_module.DisplayDriver)
    driver._lcd = SimpleNamespace(np=np)
    image = Image.new("RGB", (1, 1), (255, 0, 0))
    assert len(driver._rgb444(image)) == 3


def test_driver_show_full_frame():
    driver = object.__new__(driver_module.DisplayDriver)
    driver._lcd = MagicMock()
    driver._lcd.np = np
    driver._lcd.DC_PIN = 25
    driver._lcd.SPI.writebytes2 = MagicMock()
    driver.WIDTH = 240
    driver.HEIGHT = 240
    driver._frame_buffers = {}
    image = Image.new("RGB", (240, 240), (1, 2, 3))
    driver.show(image)
    driver._lcd.SetWindows.assert_called_once_with(0, 0, 240, 240)
    driver._lcd.SPI.writebytes2.assert_called_once()
    assert driver._last_image is image


def test_driver_show_changed_region_and_cache():
    driver = object.__new__(driver_module.DisplayDriver)
    driver._lcd = MagicMock()
    driver._lcd.np = np
    driver._lcd.DC_PIN = 25
    driver._lcd.SPI.writebytes2 = MagicMock()
    driver.WIDTH = 240
    driver.HEIGHT = 240
    driver._frame_buffers = {}

    first = Image.new("RGB", (240, 240), (0, 0, 0))
    second = first.copy()
    second.putpixel((20, 30), (255, 214, 0))
    driver.show(first)
    driver.show(second)
    calls = driver._lcd.SPI.writebytes2.call_count
    driver.show(second)
    assert driver._lcd.SPI.writebytes2.call_count == calls

    third = second.copy()
    third.putpixel((21, 30), (255, 214, 0))
    driver.show(third)
    assert driver._lcd.SetWindows.call_args.args == (21, 30, 23, 31)


def test_driver_show_rejects_wrong_size():
    driver = object.__new__(driver_module.DisplayDriver)
    driver._frame_buffers = {}
    with pytest.raises(ValueError, match="240x240"):
        driver.show(Image.new("RGB", (10, 10)))


def test_driver_show_identical_image_is_noop():
    driver = object.__new__(driver_module.DisplayDriver)
    driver._lcd = MagicMock()
    driver._lcd.np = np
    driver.WIDTH = 240
    driver.HEIGHT = 240
    driver._frame_buffers = {}
    image = Image.new("RGB", (240, 240))
    driver._last_image = image
    driver.show(image)
    driver._lcd.SPI.writebytes2.assert_not_called()


def test_close_handles_driver_error(display, caplog):
    display.driver.close = MagicMock(side_effect=RuntimeError("boom"))
    display.close()
    assert "Error while closing display" in caplog.text


def test_driver_init_and_lifecycle(monkeypatch):
    class FakeLCD:
        def __init__(self, spi_freq):
            self.spi_freq = spi_freq
            self.np = np
            self.DC_PIN = 25
            self.SPI = MagicMock()

        def Init(self):
            self.initialized = True

        def bl_DutyCycle(self, value):
            self.duty = value

        def command(self, value):
            self.command_value = value

        def data(self, value):
            self.data_value = value

        def clear(self):
            self.cleared = True

    fake_module = SimpleNamespace(LCD_1inch28=SimpleNamespace(LCD_1inch28=FakeLCD))
    monkeypatch.setitem(__import__("sys").modules, "lib", fake_module)
    monkeypatch.setenv("GLADOS_SPI_FREQ", "40000000")

    driver = driver_module.DisplayDriver()
    assert driver._lcd.spi_freq == 40000000
    assert driver._lcd.command_value == 0x3A
    assert driver._lcd.data_value == 0x03
    driver.clear()
    driver.close()
    assert driver._lcd.duty == 0


def test_driver_init_requires_waveshare_driver(monkeypatch):
    monkeypatch.setitem(__import__("sys").modules, "lib", SimpleNamespace())
    with pytest.raises(RuntimeError, match="Waveshare driver not installed"):
        driver_module.DisplayDriver()


@pytest.mark.asyncio
async def test_render_loop_error_state_uses_fast_delay(display):
    display.state = DisplayState.ERROR
    sleeps = []

    async def stop(delay):
        sleeps.append(delay)
        raise asyncio.CancelledError

    original_sleep = asyncio.sleep
    try:
        asyncio.sleep = stop
        with pytest.raises(asyncio.CancelledError):
            await display._render_loop()
    finally:
        asyncio.sleep = original_sleep

    assert sleeps == [0.05]


@pytest.mark.asyncio
async def test_render_loop_rethrows_render_error(display):
    display.render = MagicMock(side_effect=RuntimeError("boom"))

    with pytest.raises(RuntimeError, match="boom"):
        await display._render_loop()


@pytest.mark.asyncio
async def test_run_reconnect_error_path(display, monkeypatch):
    async def stop(_):
        raise asyncio.CancelledError

    def connect(*_args, **_kwargs):
        raise RuntimeError("connection failed")

    async def idle_task():
        await asyncio.Event().wait()

    monkeypatch.setattr("display.glados_display.websockets.connect", connect)
    monkeypatch.setattr("display.glados_display.asyncio.sleep", stop)
    monkeypatch.setattr(display, "_render_loop", idle_task)
    monkeypatch.setattr(display, "_event_loop_heartbeat", idle_task)

    with pytest.raises(asyncio.CancelledError):
        await display.run()

    assert display.state == DisplayState.ERROR
    assert display.connection_lost is True


def test_demo_exits_cleanly_on_keyboard_interrupt(monkeypatch):
    fake_display = MagicMock()
    monkeypatch.setattr(
        "display.glados_display.GladosDisplay",
        MagicMock(return_value=fake_display),
    )

    def stop(_):
        raise KeyboardInterrupt

    monkeypatch.setattr(
        "display.glados_display.time",
        SimpleNamespace(monotonic=lambda: 0.0, sleep=stop),
    )

    from display.glados_display import demo

    demo()
    fake_display.close.assert_called_once()
