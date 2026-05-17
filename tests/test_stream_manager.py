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
        return 0

    def read(self) -> tuple[bool, np.ndarray | None]:
        if self.index >= len(self.frames):
            return False, None
        frame = self.frames[self.index]
        self.index += 1
        return True, frame

    def set(self, prop: int, value: float) -> None:
        self.set_calls.append((prop, value))
        if prop == stream_manager.cv2.CAP_PROP_POS_FRAMES:
            self.index = int(value)

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


def test_frame_clock_sleeps_until_target_time(monkeypatch) -> None:
    perf_values = iter([10.0, 10.1])
    sleeps: list[float] = []

    monkeypatch.setattr(stream_manager.time, "perf_counter", lambda: next(perf_values))
    monkeypatch.setattr(stream_manager.time, "sleep", sleeps.append)

    clock = FrameClock(fps=2.0)
    clock.wait_next_frame()

    assert sleeps == [pytest.approx(0.4)]
