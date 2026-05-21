from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class BenchmarkStats:
    frame_count: int = 0
    skipped_frames: int = 0
    process_seconds: float = 0.0
    render_seconds: float = 0.0
    started_at: float = 0.0
    finished_at: float = 0.0
    real_time: bool = False

    def start(self) -> None:
        self.started_at = time.perf_counter()

    def finish(self) -> None:
        self.finished_at = time.perf_counter()

    @property
    def elapsed_seconds(self) -> float:
        if self.finished_at <= self.started_at:
            return 0.0
        return self.finished_at - self.started_at

    @property
    def effective_fps(self) -> float:
        elapsed = self.elapsed_seconds
        if elapsed <= 0:
            return 0.0
        return self.frame_count / elapsed

    @property
    def average_process_ms(self) -> float:
        if self.frame_count == 0:
            return 0.0
        return (self.process_seconds / self.frame_count) * 1000.0

    @property
    def average_render_ms(self) -> float:
        if self.frame_count == 0:
            return 0.0
        return (self.render_seconds / self.frame_count) * 1000.0
