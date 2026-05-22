from __future__ import annotations

import numpy as np
import pytest

from ascii_motion import __version__, stream_manager
from ascii_motion.main import (
    format_charsets,
    main,
    parse_args,
    resolve_ascii_chars,
    should_skip_late_frames,
    validate_output_mode,
)


class FakeCapture:
    def __init__(self) -> None:
        self.frames = [
            np.zeros((1, 1, 3), dtype=np.uint8),
            np.full((1, 1, 3), 255, dtype=np.uint8),
        ]
        self.index = 0

    def isOpened(self) -> bool:
        return True

    def get(self, prop: int) -> float:
        if prop == stream_manager.cv2.CAP_PROP_FPS:
            return 10.0
        if prop == stream_manager.cv2.CAP_PROP_FRAME_WIDTH:
            return 1
        if prop == stream_manager.cv2.CAP_PROP_FRAME_HEIGHT:
            return 1
        if prop == stream_manager.cv2.CAP_PROP_FRAME_COUNT:
            return len(self.frames)
        if prop == stream_manager.cv2.CAP_PROP_POS_MSEC:
            return (self.index / 10.0) * 1000.0
        return 0.0

    def read(self) -> tuple[bool, np.ndarray | None]:
        if self.index >= len(self.frames):
            return False, None
        frame = self.frames[self.index]
        self.index += 1
        return True, frame

    def grab(self) -> bool:
        if self.index >= len(self.frames):
            return False
        self.index += 1
        return True

    def set(self, prop: int, value: float) -> None:
        if prop == stream_manager.cv2.CAP_PROP_POS_MSEC:
            self.index = max(0, int((value / 1000.0) * 10.0))

    def release(self) -> None:
        return None


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


def test_parse_args_accepts_new_visual_modes() -> None:
    args = parse_args(["video.mp4", "--color", "256", "--mode", "edges", "--dither", "ordered"])

    assert args.color == "256"
    assert args.mode == "edges"
    assert args.dither == "ordered"


def test_parse_args_accepts_custom_quit_key() -> None:
    args = parse_args(["video.mp4", "--quit-key", "x"])

    assert args.quit_key == "x"


def test_parse_args_rejects_multi_character_quit_key() -> None:
    with pytest.raises(SystemExit):
        parse_args(["video.mp4", "--quit-key", "esc"])


def test_parse_args_accepts_playback_control_options() -> None:
    args = parse_args(
        [
            "video.mp4",
            "--pause-key",
            "p",
            "--backward-key",
            "j",
            "--forward-key",
            "k",
            "--seek-seconds",
            "2.5",
        ]
    )

    assert args.pause_key == "p"
    assert args.backward_key == "j"
    assert args.forward_key == "k"
    assert args.seek_seconds == 2.5


def test_parse_args_accepts_hud_and_export_options() -> None:
    args = parse_args(
        [
            "video.mp4",
            "--no-hud",
            "--no-progress",
            "--show-controls",
            "--help-key",
            "!",
            "--real-time",
            "--no-frame-skip",
            "--export",
            "out.txt",
        ]
    )

    assert args.no_hud
    assert args.no_progress
    assert args.show_controls
    assert args.help_key == "!"
    assert args.real_time
    assert args.no_frame_skip
    assert args.export == "out.txt"


def test_parse_args_rejects_invalid_seek_seconds() -> None:
    with pytest.raises(SystemExit):
        parse_args(["video.mp4", "--seek-seconds", "0"])


def test_validate_output_mode_rejects_conflicting_exports() -> None:
    args = parse_args(["video.mp4", "--preview", "--export", "out.txt"])

    with pytest.raises(ValueError, match="modo de salida"):
        validate_output_mode(args)


def test_frame_skipping_is_enabled_by_default() -> None:
    args = parse_args(["video.mp4"])

    assert should_skip_late_frames(args)


def test_frame_skipping_can_be_disabled() -> None:
    args = parse_args(["video.mp4", "--no-frame-skip"])

    assert not should_skip_late_frames(args)


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


def test_preview_prints_metadata_without_playback(monkeypatch, tmp_path, capsys) -> None:
    source = tmp_path / "video.mp4"
    source.write_bytes(b"fake")
    monkeypatch.setattr(stream_manager.cv2, "VideoCapture", lambda _source: FakeCapture())

    assert main([str(source), "--preview", "--width", "2"]) == 0

    output = capsys.readouterr().out
    assert "source_size=1x1" in output
    assert "target_size=2xauto" in output


def test_frame_at_prints_single_ascii_frame(monkeypatch, tmp_path, capsys) -> None:
    source = tmp_path / "video.mp4"
    source.write_bytes(b"fake")
    monkeypatch.setattr(stream_manager.cv2, "VideoCapture", lambda _source: FakeCapture())

    assert main([str(source), "--frame-at", "0.1", "--width", "1", "--height", "1"]) == 0

    assert capsys.readouterr().out.strip() == "@"


def test_export_writes_form_feed_separated_frames(monkeypatch, tmp_path) -> None:
    source = tmp_path / "video.mp4"
    output = tmp_path / "out.txt"
    source.write_bytes(b"fake")
    monkeypatch.setattr(stream_manager.cv2, "VideoCapture", lambda _source: FakeCapture())

    assert main([str(source), "--export", str(output), "--width", "1", "--height", "1"]) == 0

    assert output.read_text(encoding="utf-8") == " \f@"
