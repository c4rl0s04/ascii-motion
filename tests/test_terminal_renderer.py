from __future__ import annotations

from io import StringIO

from ascii_motion.terminal_renderer import TerminalRenderer


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
