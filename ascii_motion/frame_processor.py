from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from .charsets import DEFAULT_ASCII_CHARS


@dataclass(frozen=True)
class FrameProcessorConfig:
    width: int
    height: int | None = None
    ascii_chars: str = DEFAULT_ASCII_CHARS
    invert: bool = False
    terminal_char_aspect: float = 0.5


class FrameProcessor:
    """Converts BGR OpenCV frames into ASCII text buffers."""

    def __init__(self, config: FrameProcessorConfig) -> None:
        if config.width <= 0:
            raise ValueError("El ancho objetivo debe ser mayor que cero.")

        if config.height is not None and config.height <= 0:
            raise ValueError("La altura objetivo debe ser mayor que cero.")

        if config.terminal_char_aspect <= 0:
            raise ValueError("El aspect ratio de caracter debe ser mayor que cero.")

        if len(config.ascii_chars) < 2:
            raise ValueError("La escala ASCII debe contener al menos dos caracteres.")

        self.config = config
        chars = config.ascii_chars[::-1] if config.invert else config.ascii_chars
        self._ascii_lut = np.array(list(chars), dtype="<U1")

    def process(self, frame_bgr: np.ndarray) -> str:
        resized = self._resize_preserving_terminal_aspect(frame_bgr)
        luminance = self._luminance_from_bgr(resized)
        char_matrix = self._map_luminance_to_ascii(luminance)
        return self._ascii_matrix_to_text(char_matrix)

    def _resize_preserving_terminal_aspect(self, frame_bgr: np.ndarray) -> np.ndarray:
        source_height, source_width = frame_bgr.shape[:2]
        target_width = self.config.width

        if self.config.height is None:
            target_height = int(
                (source_height / source_width)
                * target_width
                * self.config.terminal_char_aspect
            )
            target_height = max(1, target_height)
        else:
            target_height = self.config.height

        return cv2.resize(
            frame_bgr,
            (target_width, target_height),
            interpolation=cv2.INTER_AREA,
        )

    @staticmethod
    def _luminance_from_bgr(frame_bgr: np.ndarray) -> np.ndarray:
        frame = frame_bgr.astype(np.float32, copy=False)
        return (
            (0.2126 * frame[:, :, 2])
            + (0.7152 * frame[:, :, 1])
            + (0.0722 * frame[:, :, 0])
        )

    def _map_luminance_to_ascii(self, luminance: np.ndarray) -> np.ndarray:
        normalized = np.clip(luminance, 0, 255) / 255.0
        indexes = (normalized * (len(self._ascii_lut) - 1)).astype(np.int16)
        return self._ascii_lut[indexes]

    @staticmethod
    def _ascii_matrix_to_text(char_matrix: np.ndarray) -> str:
        return "\n".join("".join(row) for row in char_matrix)
