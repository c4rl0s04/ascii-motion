from __future__ import annotations

import select
import sys
import termios
import tty
from types import TracebackType
from typing import TextIO

PlaybackAction = str

ACTION_NONE = "none"
ACTION_QUIT = "quit"
ACTION_PAUSE = "pause"
ACTION_BACKWARD = "backward"
ACTION_FORWARD = "forward"
ACTION_HELP = "help"


class KeyboardController:
    """Non-blocking keyboard reader for interactive terminal playback."""

    LEFT_ARROW = "\033[D"
    RIGHT_ARROW = "\033[C"

    def __init__(
        self,
        quit_key: str = "q",
        pause_key: str = " ",
        backward_key: str = "h",
        forward_key: str = "l",
        help_key: str = "?",
        stdin: TextIO | None = None,
    ) -> None:
        if len(quit_key) != 1:
            raise ValueError("La tecla de salida debe ser un unico caracter.")
        if len(pause_key) != 1:
            raise ValueError("La tecla de pausa debe ser un unico caracter.")
        if len(backward_key) != 1:
            raise ValueError("La tecla de retroceso debe ser un unico caracter.")
        if len(forward_key) != 1:
            raise ValueError("La tecla de avance debe ser un unico caracter.")
        if len(help_key) != 1:
            raise ValueError("La tecla de ayuda debe ser un unico caracter.")

        self.quit_key = quit_key
        self.pause_key = pause_key
        self.backward_key = backward_key
        self.forward_key = forward_key
        self.help_key = help_key
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
        return self.read_action() == ACTION_QUIT

    def read_action(self) -> PlaybackAction:
        if self._fd is None:
            return ACTION_NONE

        readable, _, _ = select.select([self._stdin], [], [], 0)
        if not readable:
            return ACTION_NONE

        key = self._read_key_sequence()

        if key.lower() == self.quit_key.lower():
            return ACTION_QUIT
        if key.lower() == self.pause_key.lower():
            return ACTION_PAUSE
        if key.lower() == self.backward_key.lower() or key == self.LEFT_ARROW:
            return ACTION_BACKWARD
        if key.lower() == self.forward_key.lower() or key == self.RIGHT_ARROW:
            return ACTION_FORWARD
        if key.lower() == self.help_key.lower():
            return ACTION_HELP

        return ACTION_NONE

    def _read_key_sequence(self) -> str:
        key = self._stdin.read(1)

        if key != "\033":
            return key

        sequence = [key]
        while True:
            readable, _, _ = select.select([self._stdin], [], [], 0)
            if not readable:
                break
            sequence.append(self._stdin.read(1))
            if len(sequence) >= 3:
                break

        return "".join(sequence)

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
