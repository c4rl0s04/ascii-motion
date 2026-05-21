from __future__ import annotations

from ascii_motion import keyboard
from ascii_motion.keyboard import (
    ACTION_BACKWARD,
    ACTION_FORWARD,
    ACTION_HELP,
    ACTION_NONE,
    ACTION_PAUSE,
    ACTION_QUIT,
    KeyboardController,
)


class FakeStdin:
    def __init__(self, chars: str = "", tty: bool = True) -> None:
        self.chars = chars
        self.tty = tty

    def isatty(self) -> bool:
        return self.tty

    def fileno(self) -> int:
        return 7

    def read(self, _size: int) -> str:
        char = self.chars[:1]
        self.chars = self.chars[1:]
        return char


def test_keyboard_controller_is_disabled_for_non_tty() -> None:
    controller = KeyboardController(stdin=FakeStdin(tty=False))

    controller.start()

    assert not controller.enabled
    assert not controller.should_quit()


def patch_interactive_terminal(monkeypatch) -> None:
    monkeypatch.setattr(keyboard.termios, "tcgetattr", lambda _fd: [0])
    monkeypatch.setattr(keyboard.termios, "tcsetattr", lambda *_args: None)
    monkeypatch.setattr(keyboard.tty, "setcbreak", lambda _fd: None)
    monkeypatch.setattr(
        keyboard.select,
        "select",
        lambda read, _write, _err, _timeout: (read, [], []),
    )


def test_keyboard_controller_detects_quit_key(monkeypatch) -> None:
    stdin = FakeStdin(chars="q")
    controller = KeyboardController(stdin=stdin)
    patch_interactive_terminal(monkeypatch)

    with controller:
        assert controller.enabled
        assert controller.should_quit()

    assert not controller.enabled


def test_keyboard_controller_ignores_other_keys(monkeypatch) -> None:
    stdin = FakeStdin(chars="x")
    controller = KeyboardController(stdin=stdin)
    patch_interactive_terminal(monkeypatch)

    with controller:
        assert not controller.should_quit()


def test_keyboard_controller_maps_playback_actions(monkeypatch) -> None:
    stdin = FakeStdin(chars="q hl?")
    controller = KeyboardController(stdin=stdin)
    patch_interactive_terminal(monkeypatch)

    with controller:
        assert controller.read_action() == ACTION_QUIT
        assert controller.read_action() == ACTION_PAUSE
        assert controller.read_action() == ACTION_BACKWARD
        assert controller.read_action() == ACTION_FORWARD
        assert controller.read_action() == ACTION_HELP


def test_keyboard_controller_maps_arrow_keys(monkeypatch) -> None:
    stdin = FakeStdin(chars="\033[D\033[C")
    controller = KeyboardController(stdin=stdin)
    patch_interactive_terminal(monkeypatch)

    with controller:
        assert controller.read_action() == ACTION_BACKWARD
        assert controller.read_action() == ACTION_FORWARD


def test_keyboard_controller_returns_none_without_input(monkeypatch) -> None:
    stdin = FakeStdin(chars="")
    controller = KeyboardController(stdin=stdin)

    monkeypatch.setattr(keyboard.termios, "tcgetattr", lambda _fd: [0])
    monkeypatch.setattr(keyboard.termios, "tcsetattr", lambda *_args: None)
    monkeypatch.setattr(keyboard.tty, "setcbreak", lambda _fd: None)
    monkeypatch.setattr(
        keyboard.select,
        "select",
        lambda _read, _write, _err, _timeout: ([], [], []),
    )

    with controller:
        assert controller.read_action() == ACTION_NONE
