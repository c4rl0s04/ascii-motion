from __future__ import annotations

import numpy as np
import pytest

from ascii_motion import stream_manager
from ascii_motion.stream_manager import DEFAULT_FPS, FrameClock, StreamManager


class FakeCapture:
    def __init__(self, frames: list[np.ndarray] | None = None, fps: float = 24.0) -> None:
        self.frames = frames or []
        self.fps = fps
        self.index = 0
        self.set_calls: list[tuple[int, float]] = []
        self.released = False

    def isOpened(self) -> bool:
        return True

    def get(self, prop: int) -> float:
        if prop == stream_manager.cv2.CAP_PROP_FPS:
            return self.fps
        if prop == stream_manager.cv2.CAP_PROP_FRAME_WIDTH:
            return 640
        if prop == stream_manager.cv2.CAP_PROP_FRAME_HEIGHT:
            return 360
        if prop == stream_manager.cv2.CAP_PROP_FRAME_COUNT:
            return len(self.frames)
        if prop == stream_manager.cv2.CAP_PROP_POS_MSEC:
            return (self.index / self.fps) * 1000.0
        return 0

    def read(self) -> tuple[bool, np.ndarray | None]:
        if self.index >= len(self.frames):
            return False, None
        frame = self.frames[self.index]
        self.index += 1
        return True, frame

    def grab(self) -> bool:
        if self.index >= len(self.frames):
            return False
        self.index += 1
        return True

    def set(self, prop: int, value: float) -> None:
        self.set_calls.append((prop, value))
        if prop == stream_manager.cv2.CAP_PROP_POS_FRAMES:
            self.index = int(value)
        if prop == stream_manager.cv2.CAP_PROP_POS_MSEC:
            self.index = max(0, int((value / 1000.0) * self.fps))

    def release(self) -> None:
        self.released = True


def test_stream_manager_reads_metadata(monkeypatch) -> None:
    fake = FakeCapture(fps=60.0)
    monkeypatch.setattr(stream_manager.cv2, "VideoCapture", lambda _source: fake)

    manager = StreamManager("0")

    assert manager.source == 0
    assert manager.metadata.fps == 60.0
    assert manager.metadata.width == 640
    assert manager.metadata.height == 360


def test_stream_manager_falls_back_to_default_fps(monkeypatch) -> None:
    fake = FakeCapture(fps=0.0)
    monkeypatch.setattr(stream_manager.cv2, "VideoCapture", lambda _source: fake)

    manager = StreamManager("0")

    assert manager.metadata.fps == DEFAULT_FPS


def test_stream_manager_yields_until_end(monkeypatch) -> None:
    frames = [np.zeros((1, 1, 3), dtype=np.uint8), np.ones((1, 1, 3), dtype=np.uint8)]
    fake = FakeCapture(frames=frames)
    monkeypatch.setattr(stream_manager.cv2, "VideoCapture", lambda _source: fake)

    manager = StreamManager("0")

    assert list(manager.frames()) == frames


def test_validate_file_source_rejects_missing_path() -> None:
    with pytest.raises(ValueError, match="no existe"):
        StreamManager.validate_file_source("/path/that/does/not/exist.mp4")


def test_stream_manager_seeks_relative_to_current_position(monkeypatch) -> None:
    frames = [np.zeros((1, 1, 3), dtype=np.uint8) for _ in range(20)]
    fake = FakeCapture(frames=frames, fps=10.0)
    fake.index = 5
    monkeypatch.setattr(stream_manager.cv2, "VideoCapture", lambda _source: fake)

    manager = StreamManager("0")
    manager.seek_relative(2.0)

    assert fake.set_calls[-1] == (stream_manager.cv2.CAP_PROP_POS_MSEC, 2500.0)


def test_stream_manager_relative_seek_clamps_to_start(monkeypatch) -> None:
    frames = [np.zeros((1, 1, 3), dtype=np.uint8) for _ in range(20)]
    fake = FakeCapture(frames=frames, fps=10.0)
    fake.index = 5
    monkeypatch.setattr(stream_manager.cv2, "VideoCapture", lambda _source: fake)

    manager = StreamManager("0")
    manager.seek_relative(-10.0)

    assert fake.set_calls[-1] == (stream_manager.cv2.CAP_PROP_POS_MSEC, 0.0)


def test_stream_manager_skips_frames_with_grab(monkeypatch) -> None:
    frames = [np.zeros((1, 1, 3), dtype=np.uint8) for _ in range(3)]
    fake = FakeCapture(frames=frames, fps=10.0)
    monkeypatch.setattr(stream_manager.cv2, "VideoCapture", lambda _source: fake)

    manager = StreamManager("0")

    assert manager.skip_frames(2) == 2
    assert fake.index == 2


def test_frame_clock_sleeps_until_target_time(monkeypatch) -> None:
    perf_values = iter([10.0, 10.1])
    sleeps: list[float] = []

    monkeypatch.setattr(stream_manager.time, "perf_counter", lambda: next(perf_values))
    monkeypatch.setattr(stream_manager.time, "sleep", sleeps.append)

    clock = FrameClock(fps=2.0)
    clock.wait_next_frame()

    assert sleeps == [pytest.approx(0.4)]


def test_frame_clock_reset_restarts_schedule(monkeypatch) -> None:
    perf_values = iter([10.0, 10.2, 10.3])
    sleeps: list[float] = []

    monkeypatch.setattr(stream_manager.time, "perf_counter", lambda: next(perf_values))
    monkeypatch.setattr(stream_manager.time, "sleep", sleeps.append)

    clock = FrameClock(fps=10.0)
    clock.reset()
    clock.wait_next_frame()

    assert sleeps == []


def test_frame_clock_reports_frames_to_skip_when_late(monkeypatch) -> None:
    perf_values = iter([10.0, 10.45])

    monkeypatch.setattr(stream_manager.time, "perf_counter", lambda: next(perf_values))

    clock = FrameClock(fps=10.0)
    clock.frame_index = 1

    assert clock.frames_to_skip() == 3
