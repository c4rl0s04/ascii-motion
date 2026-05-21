from __future__ import annotations

import pytest

from ascii_motion import __version__
from ascii_motion.main import format_charsets, main, parse_args, resolve_ascii_chars


def test_parse_args_rejects_non_positive_width() -> None:
    with pytest.raises(SystemExit):
        parse_args(["video.mp4", "--width", "0"])


def test_parse_args_rejects_non_positive_fps() -> None:
    with pytest.raises(SystemExit):
        parse_args(["video.mp4", "--fps", "-1"])


def test_custom_charset_requires_chars() -> None:
    with pytest.raises(ValueError, match="requiere --chars"):
        resolve_ascii_chars("custom", None)


def test_charset_can_be_overridden_with_chars() -> None:
    assert resolve_ascii_chars("classic", "ab") == "ab"


def test_parse_args_accepts_truecolor_mode() -> None:
    args = parse_args(["video.mp4", "--color", "truecolor"])

    assert args.color == "truecolor"


def test_parse_args_accepts_custom_quit_key() -> None:
    args = parse_args(["video.mp4", "--quit-key", "x"])

    assert args.quit_key == "x"


def test_parse_args_rejects_multi_character_quit_key() -> None:
    with pytest.raises(SystemExit):
        parse_args(["video.mp4", "--quit-key", "esc"])


def test_list_charsets_does_not_require_source(capsys) -> None:
    assert main(["--list-charsets"]) == 0

    output = capsys.readouterr().out
    assert "classic" in output
    assert "dense" in output
    assert "blocks" in output
    assert "custom" in output


def test_format_charsets_includes_visible_space_marker() -> None:
    assert "classic ·.:-=+*#%@" in format_charsets()


def test_version_prints_package_version(capsys) -> None:
    with pytest.raises(SystemExit) as exc_info:
        parse_args(["--version"])

    assert exc_info.value.code == 0
    assert f"ascii-motion {__version__}" in capsys.readouterr().out


def test_source_is_required_for_playback(capsys) -> None:
    assert main([]) == 1

    assert "Debes indicar una ruta de video" in capsys.readouterr().err
