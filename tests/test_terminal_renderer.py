from __future__ import annotations

from io import StringIO

from ascii_motion.terminal_renderer import PlaybackStatus, TerminalRenderer


def test_renderer_uses_alt_screen_and_restores_cursor() -> None:
    output = StringIO()
    renderer = TerminalRenderer(use_alt_screen=True, stdout=output)

    renderer.start()
    renderer.stop()

    text = output.getvalue()
    assert TerminalRenderer.ALT_SCREEN_ON in text
    assert TerminalRenderer.HIDE_CURSOR in text
    assert TerminalRenderer.SHOW_CURSOR in text
    assert TerminalRenderer.ALT_SCREEN_OFF in text


def test_render_repositions_cursor_without_clearing_screen_each_frame() -> None:
    output = StringIO()
    renderer = TerminalRenderer(use_alt_screen=False, stdout=output)

    renderer.render("ab\ncd")
    renderer.render("ef\ngh")

    text = output.getvalue()
    assert text.count(TerminalRenderer.CURSOR_HOME) == 2
    assert TerminalRenderer.CLEAR_SCREEN not in text


def test_renderer_composes_hud_progress_and_controls() -> None:
    status = PlaybackStatus(
        current_seconds=10.0,
        total_seconds=20.0,
        effective_fps=29.9,
        target_fps=30.0,
        width=80,
        height=24,
        paused=True,
        color_mode="none",
        processor_mode="ascii",
    )

    output = TerminalRenderer.compose_frame(
        "abc",
        status=status,
        show_hud=True,
        show_progress=True,
        show_controls=True,
    )

    assert "00:10 / 00:20" in output
    assert "paused" in output
    assert "50.0%" in output
    assert "? help" in output


def test_renderer_can_hide_hud_progress_and_controls() -> None:
    status = PlaybackStatus(
        current_seconds=10.0,
        total_seconds=20.0,
        effective_fps=29.9,
        target_fps=30.0,
        width=80,
        height=24,
        paused=False,
        color_mode="none",
        processor_mode="ascii",
    )

    assert TerminalRenderer.compose_frame("abc", status=status) == "abc"
