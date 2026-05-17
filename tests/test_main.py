from __future__ import annotations

import pytest

from ascii_motion.main import parse_args, resolve_ascii_chars


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
