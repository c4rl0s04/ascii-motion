from __future__ import annotations

import time
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

DEFAULT_FPS = 30.0


@dataclass(frozen=True)
class VideoMetadata:
    fps: float
    width: int
    height: int
    frame_count: int


class StreamManager:
    """Thin wrapper around cv2.VideoCapture with frame-rate metadata."""

    def __init__(self, source: str | int, loop: bool = False) -> None:
        self.source = self.normalize_source(source)
        self.loop = loop
        self._capture = cv2.VideoCapture(self.source)

        if not self._capture.isOpened():
            raise RuntimeError(f"No se pudo abrir la fuente de video: {source}")

        self.metadata = self._read_metadata()

    @staticmethod
    def is_camera_index(source: str | int) -> bool:
        return isinstance(source, int) or source.isdigit()

    @staticmethod
    def normalize_source(source: str | int) -> str | int:
        if isinstance(source, int):
            return source

        if source.isdigit():
            return int(source)

        return str(Path(source).expanduser())

    @staticmethod
    def validate_file_source(source: str | int) -> None:
        if isinstance(source, int) or source.isdigit():
            return

        path = Path(source).expanduser()
        if not path.exists():
            raise ValueError(f"El archivo de video no existe: {path}")

        if not path.is_file():
            raise ValueError(f"La fuente no es un archivo regular: {path}")

    def _read_metadata(self) -> VideoMetadata:
        fps = float(self._capture.get(cv2.CAP_PROP_FPS) or 0.0)
        width = int(self._capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(self._capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        frame_count = int(self._capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

        if fps <= 1e-6:
            fps = DEFAULT_FPS

        return VideoMetadata(fps=fps, width=width, height=height, frame_count=frame_count)

    def seek(self, seconds: float) -> None:
        if seconds <= 0:
            return
        self._capture.set(cv2.CAP_PROP_POS_MSEC, seconds * 1000.0)

    def frames(self) -> Iterator[np.ndarray]:
        while True:
            ok, frame = self._capture.read()

            if ok:
                yield frame
                continue

            if not self.loop:
                break

            self._capture.set(cv2.CAP_PROP_POS_FRAMES, 0)

    def release(self) -> None:
        self._capture.release()

    def __enter__(self) -> StreamManager:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.release()


class FrameClock:
    """Frame pacing helper based on a monotonic clock."""

    def __init__(self, fps: float) -> None:
        self.frame_interval = 1.0 / max(fps, 1e-6)
        self.started_at = time.perf_counter()
        self.frame_index = 0

    def wait_next_frame(self) -> None:
        self.frame_index += 1
        target_time = self.started_at + (self.frame_index * self.frame_interval)
        delay = target_time - time.perf_counter()

        if delay > 0:
            time.sleep(delay)
