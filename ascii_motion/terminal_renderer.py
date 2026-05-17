from __future__ import annotations

import shutil
import sys
from dataclasses import dataclass
from typing import TextIO


@dataclass(frozen=True)
class TerminalSize:
    columns: int
    rows: int


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

    def render(self, ascii_frame: str) -> None:
        frame_height = ascii_frame.count("\n") + 1 if ascii_frame else 0
        padding = ""

        if self._last_height > frame_height:
            padding = "\n" * (self._last_height - frame_height)

        self._stdout.write(self.CURSOR_HOME + ascii_frame + padding)
        self._stdout.flush()
        self._last_height = frame_height

    def stop(self) -> None:
        suffix = self.ALT_SCREEN_OFF if self.use_alt_screen else "\n"
        self._stdout.write(self.RESET_STYLE + self.SHOW_CURSOR + suffix)
        self._stdout.flush()

    def __enter__(self) -> TerminalRenderer:
        self.start()
        return self

    def __exit__(self, *_exc: object) -> None:
        self.stop()
