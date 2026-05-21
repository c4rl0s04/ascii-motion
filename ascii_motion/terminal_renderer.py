from __future__ import annotations

import shutil
import sys
from dataclasses import dataclass
from typing import TextIO


@dataclass(frozen=True)
class TerminalSize:
    columns: int
    rows: int


@dataclass(frozen=True)
class PlaybackStatus:
    current_seconds: float
    total_seconds: float | None
    effective_fps: float
    target_fps: float
    width: int
    height: int
    paused: bool
    color_mode: str
    processor_mode: str
    skipped_frames: int = 0


class TerminalRenderer:
    """ANSI terminal renderer optimized to avoid full-screen clears per frame."""

    ALT_SCREEN_ON = "\033[?1049h"
    ALT_SCREEN_OFF = "\033[?1049l"
    CLEAR_SCREEN = "\033[2J"
    CURSOR_HOME = "\033[H"
    HIDE_CURSOR = "\033[?25l"
    SHOW_CURSOR = "\033[?25h"
    RESET_STYLE = "\033[0m"

    def __init__(self, use_alt_screen: bool = True, stdout: TextIO | None = None) -> None:
        self.use_alt_screen = use_alt_screen
        self._stdout = stdout or sys.stdout
        self._last_height = 0

    @staticmethod
    def terminal_size(default_columns: int = 120, default_rows: int = 24) -> TerminalSize:
        size = shutil.get_terminal_size(fallback=(default_columns, default_rows))
        return TerminalSize(columns=size.columns, rows=size.lines)

    @staticmethod
    def terminal_width(default: int = 120) -> int:
        return TerminalRenderer.terminal_size(default_columns=default).columns

    def start(self) -> None:
        prefix = self.ALT_SCREEN_ON if self.use_alt_screen else ""
        self._stdout.write(prefix + self.HIDE_CURSOR + self.CLEAR_SCREEN + self.CURSOR_HOME)
        self._stdout.flush()

    @staticmethod
    def reserved_rows(
        show_hud: bool = True,
        show_progress: bool = True,
        show_controls: bool = False,
    ) -> int:
        return int(show_hud) + int(show_progress) + int(show_controls)

    def render(
        self,
        ascii_frame: str,
        status: PlaybackStatus | None = None,
        show_hud: bool = False,
        show_progress: bool = False,
        show_controls: bool = False,
    ) -> None:
        output = self.compose_frame(
            ascii_frame,
            status=status,
            show_hud=show_hud,
            show_progress=show_progress,
            show_controls=show_controls,
        )
        frame_height = output.count("\n") + 1 if output else 0
        padding = ""

        if self._last_height > frame_height:
            padding = "\n" * (self._last_height - frame_height)

        self._stdout.write(self.CURSOR_HOME + output + padding)
        self._stdout.flush()
        self._last_height = frame_height

    @classmethod
    def compose_frame(
        cls,
        ascii_frame: str,
        status: PlaybackStatus | None = None,
        show_hud: bool = False,
        show_progress: bool = False,
        show_controls: bool = False,
    ) -> str:
        lines = [ascii_frame]

        if status is not None and show_hud:
            lines.append(cls._format_hud(status))

        if status is not None and show_progress:
            lines.append(cls._format_progress(status))

        if show_controls:
            lines.append("q quit | space pause | left/right seek | h/l fallback | ? help")

        return "\n".join(line for line in lines if line != "")

    @staticmethod
    def _format_time(seconds: float | None) -> str:
        if seconds is None:
            return "--:--"
        seconds = max(0, int(seconds))
        minutes, secs = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours:d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"

    @classmethod
    def _format_hud(cls, status: PlaybackStatus) -> str:
        state = "paused" if status.paused else "playing"
        return (
            f"{cls._format_time(status.current_seconds)} / "
            f"{cls._format_time(status.total_seconds)} | "
            f"{status.effective_fps:.1f}/{status.target_fps:.1f} FPS | "
            f"{status.width}x{status.height} | "
            f"{status.processor_mode} | {status.color_mode} | "
            f"skipped={status.skipped_frames} | {state}"
        )

    @classmethod
    def _format_progress(cls, status: PlaybackStatus, width: int = 28) -> str:
        if status.total_seconds is None or status.total_seconds <= 0:
            return "[" + ("-" * width) + "] --%"

        ratio = min(1.0, max(0.0, status.current_seconds / status.total_seconds))
        filled = int(ratio * width)
        return "[" + ("#" * filled) + ("-" * (width - filled)) + f"] {ratio * 100:5.1f}%"

    def stop(self) -> None:
        suffix = self.ALT_SCREEN_OFF if self.use_alt_screen else "\n"
        self._stdout.write(self.RESET_STYLE + self.SHOW_CURSOR + suffix)
        self._stdout.flush()

    def __enter__(self) -> TerminalRenderer:
        self.start()
        return self

    def __exit__(self, *_exc: object) -> None:
        self.stop()
