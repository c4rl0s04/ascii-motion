from __future__ import annotations

from ascii_motion import keyboard
from ascii_motion.keyboard import KeyboardController


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


def test_keyboard_controller_detects_quit_key(monkeypatch) -> None:
    stdin = FakeStdin(chars="q")
    controller = KeyboardController(stdin=stdin)

    monkeypatch.setattr(keyboard.termios, "tcgetattr", lambda _fd: [0])
    monkeypatch.setattr(keyboard.termios, "tcsetattr", lambda *_args: None)
    monkeypatch.setattr(keyboard.tty, "setcbreak", lambda _fd: None)
    monkeypatch.setattr(
        keyboard.select,
        "select",
        lambda read, _write, _err, _timeout: (read, [], []),
    )

    with controller:
        assert controller.enabled
        assert controller.should_quit()

    assert not controller.enabled


def test_keyboard_controller_ignores_other_keys(monkeypatch) -> None:
    stdin = FakeStdin(chars="x")
    controller = KeyboardController(stdin=stdin)

    monkeypatch.setattr(keyboard.termios, "tcgetattr", lambda _fd: [0])
    monkeypatch.setattr(keyboard.termios, "tcsetattr", lambda *_args: None)
    monkeypatch.setattr(keyboard.tty, "setcbreak", lambda _fd: None)
    monkeypatch.setattr(
        keyboard.select,
        "select",
        lambda read, _write, _err, _timeout: (read, [], []),
    )

    with controller:
        assert not controller.should_quit()
