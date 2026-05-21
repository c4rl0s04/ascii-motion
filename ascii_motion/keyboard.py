from __future__ import annotations

import select
import sys
import termios
import tty
from types import TracebackType
from typing import TextIO


class KeyboardController:
    """Non-blocking keyboard reader for interactive terminal playback."""

    def __init__(self, quit_key: str = "q", stdin: TextIO | None = None) -> None:
        if len(quit_key) != 1:
            raise ValueError("La tecla de salida debe ser un unico caracter.")

        self.quit_key = quit_key
        self._stdin = stdin or sys.stdin
        self._fd: int | None = None
        self._previous_settings: list[int | bytes] | None = None

    @property
    def enabled(self) -> bool:
        return self._fd is not None

    def start(self) -> None:
        if not self._stdin.isatty():
            return

        self._fd = self._stdin.fileno()
        self._previous_settings = termios.tcgetattr(self._fd)
        tty.setcbreak(self._fd)

    def should_quit(self) -> bool:
        if self._fd is None:
            return False

        readable, _, _ = select.select([self._stdin], [], [], 0)
        if not readable:
            return False

        return self._stdin.read(1).lower() == self.quit_key.lower()

    def stop(self) -> None:
        if self._fd is None or self._previous_settings is None:
            return

        termios.tcsetattr(self._fd, termios.TCSADRAIN, self._previous_settings)
        self._fd = None
        self._previous_settings = None

    def __enter__(self) -> KeyboardController:
        self.start()
        return self

    def __exit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc: BaseException | None,
        _traceback: TracebackType | None,
    ) -> None:
        self.stop()
