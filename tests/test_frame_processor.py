from __future__ import annotations

import numpy as np

from ascii_motion.frame_processor import ANSI_RESET, FrameProcessor, FrameProcessorConfig


def test_luminance_uses_rec_709_coefficients_for_bgr_frames() -> None:
    frame = np.array([[[10, 20, 30], [100, 150, 200]]], dtype=np.uint8)

    luminance = FrameProcessor._luminance_from_bgr(frame)

    expected = np.array(
        [
            [
                (0.2126 * 30) + (0.7152 * 20) + (0.0722 * 10),
                (0.2126 * 200) + (0.7152 * 150) + (0.0722 * 100),
            ]
        ],
        dtype=np.float32,
    )
    np.testing.assert_allclose(luminance, expected, rtol=1e-5)


def test_resize_height_accounts_for_terminal_character_aspect(monkeypatch) -> None:
    captured_size = None

    def fake_resize(frame: np.ndarray, size: tuple[int, int], interpolation: int) -> np.ndarray:
        nonlocal captured_size
        captured_size = size
        return np.zeros((size[1], size[0], 3), dtype=frame.dtype)

    monkeypatch.setattr("ascii_motion.frame_processor.cv2.resize", fake_resize)

    processor = FrameProcessor(FrameProcessorConfig(width=100, terminal_char_aspect=0.5))
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)

    resized = processor._resize_preserving_terminal_aspect(frame)

    assert captured_size == (100, 28)
    assert resized.shape == (28, 100, 3)


def test_auto_resize_can_fit_vertical_video_within_max_height(monkeypatch) -> None:
    captured_size = None

    def fake_resize(frame: np.ndarray, size: tuple[int, int], interpolation: int) -> np.ndarray:
        nonlocal captured_size
        captured_size = size
        return np.zeros((size[1], size[0], 3), dtype=frame.dtype)

    monkeypatch.setattr("ascii_motion.frame_processor.cv2.resize", fake_resize)

    processor = FrameProcessor(
        FrameProcessorConfig(width=80, max_height=20, terminal_char_aspect=0.5)
    )
    frame = np.zeros((1920, 1080, 3), dtype=np.uint8)

    resized = processor._resize_preserving_terminal_aspect(frame)

    assert captured_size == (22, 20)
    assert resized.shape == (20, 22, 3)


def test_ascii_mapping_uses_dark_to_light_extremes() -> None:
    processor = FrameProcessor(FrameProcessorConfig(width=2, ascii_chars=" .#"))
    luminance = np.array([[0, 255]], dtype=np.float32)

    mapped = processor._map_luminance_to_ascii(luminance)

    assert mapped.tolist() == [[" ", "#"]]


def test_ascii_mapping_can_be_inverted() -> None:
    processor = FrameProcessor(FrameProcessorConfig(width=2, ascii_chars=" .#", invert=True))
    luminance = np.array([[0, 255]], dtype=np.float32)

    mapped = processor._map_luminance_to_ascii(luminance)

    assert mapped.tolist() == [["#", " "]]


def test_process_returns_text_without_pixel_nested_loops() -> None:
    processor = FrameProcessor(FrameProcessorConfig(width=2, height=1, ascii_chars=" .#"))
    frame = np.array([[[0, 0, 0], [255, 255, 255]]], dtype=np.uint8)

    assert processor.process(frame) == " #"


def test_process_can_emit_truecolor_ansi_cells() -> None:
    processor = FrameProcessor(
        FrameProcessorConfig(width=2, height=1, ascii_chars=" .#", color_mode="truecolor")
    )
    frame = np.array([[[10, 20, 30], [200, 210, 220]]], dtype=np.uint8)

    assert processor.process(frame) == (
        "\033[38;2;30;20;10m "
        "\033[38;2;220;210;200m."
        f"{ANSI_RESET}"
    )


def test_process_can_emit_256_color_ansi_cells() -> None:
    processor = FrameProcessor(FrameProcessorConfig(width=1, height=1, color_mode="256"))
    frame = np.array([[[0, 0, 255]]], dtype=np.uint8)

    assert processor.process(frame) == "\033[38;5;196m.\033[0m"


def test_process_can_emit_grayscale_ansi_cells() -> None:
    processor = FrameProcessor(FrameProcessorConfig(width=1, height=1, color_mode="grayscale"))
    frame = np.array([[[255, 255, 255]]], dtype=np.uint8)

    assert processor.process(frame) == "\033[38;5;255m@\033[0m"


def test_edge_mode_emphasizes_boundaries() -> None:
    processor = FrameProcessor(FrameProcessorConfig(width=3, height=3, processor_mode="edges"))
    luminance = np.array(
        [
            [0, 0, 255],
            [0, 0, 255],
            [0, 0, 255],
        ],
        dtype=np.float32,
    )

    edges = processor._apply_processor_mode(luminance)

    assert edges.max() == 255
    assert edges[:, 1].mean() > edges[:, 0].mean()


def test_ordered_dither_changes_luminance_matrix() -> None:
    processor = FrameProcessor(FrameProcessorConfig(width=4, height=4, dither_mode="ordered"))
    luminance = np.full((4, 4), 128, dtype=np.float32)

    dithered = processor._apply_dither(luminance)

    assert not np.array_equal(dithered, luminance)


def test_invalid_color_mode_is_rejected() -> None:
    config = FrameProcessorConfig(width=2, color_mode="invalid")  # type: ignore[arg-type]

    try:
        FrameProcessor(config)
    except ValueError as exc:
        assert "modo de color" in str(exc)
    else:
        raise AssertionError("Expected invalid color mode to fail.")
