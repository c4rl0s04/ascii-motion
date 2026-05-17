from __future__ import annotations

import numpy as np

from ascii_motion.frame_processor import FrameProcessor, FrameProcessorConfig


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
