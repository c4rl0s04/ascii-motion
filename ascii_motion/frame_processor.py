from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import cv2
import numpy as np

from .charsets import DEFAULT_ASCII_CHARS

ColorMode = Literal["none", "truecolor", "256", "grayscale"]
ProcessorMode = Literal["ascii", "edges", "hybrid"]
DitherMode = Literal["none", "ordered"]
ANSI_RESET = "\033[0m"


@dataclass(frozen=True)
class FrameProcessorConfig:
    width: int
    height: int | None = None
    ascii_chars: str = DEFAULT_ASCII_CHARS
    invert: bool = False
    color_mode: ColorMode = "none"
    processor_mode: ProcessorMode = "ascii"
    dither_mode: DitherMode = "none"
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

        if config.color_mode not in ("none", "truecolor", "256", "grayscale"):
            raise ValueError("El modo de color debe ser 'none', 'truecolor', '256' o 'grayscale'.")

        if config.processor_mode not in ("ascii", "edges", "hybrid"):
            raise ValueError("El modo de procesador debe ser 'ascii', 'edges' o 'hybrid'.")

        if config.dither_mode not in ("none", "ordered"):
            raise ValueError("El modo de dithering debe ser 'none' u 'ordered'.")

        self.config = config
        chars = config.ascii_chars[::-1] if config.invert else config.ascii_chars
        self._ascii_lut = np.array(list(chars), dtype="<U1")

    def process(self, frame_bgr: np.ndarray) -> str:
        resized = self._resize_preserving_terminal_aspect(frame_bgr)
        luminance = self._luminance_from_bgr(resized)
        mapped_luminance = self._apply_processor_mode(luminance)
        dithered_luminance = self._apply_dither(mapped_luminance)
        char_matrix = self._map_luminance_to_ascii(dithered_luminance)

        if self.config.color_mode == "truecolor":
            return self._ascii_matrix_to_truecolor_text(char_matrix, resized)
        if self.config.color_mode == "256":
            return self._ascii_matrix_to_256color_text(char_matrix, resized)
        if self.config.color_mode == "grayscale":
            return self._ascii_matrix_to_grayscale_text(char_matrix, luminance)

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

    def _apply_processor_mode(self, luminance: np.ndarray) -> np.ndarray:
        if self.config.processor_mode == "ascii":
            return luminance

        edges = self._edge_luminance(luminance)
        if self.config.processor_mode == "edges":
            return edges

        return np.clip((luminance * 0.65) + (edges * 0.35), 0, 255)

    @staticmethod
    def _edge_luminance(luminance: np.ndarray) -> np.ndarray:
        gray = np.clip(luminance, 0, 255).astype(np.uint8)
        grad_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
        magnitude = cv2.magnitude(grad_x, grad_y)
        max_value = float(magnitude.max(initial=0.0))
        if max_value <= 1e-6:
            return np.zeros_like(luminance, dtype=np.float32)
        return (magnitude / max_value) * 255.0

    def _apply_dither(self, luminance: np.ndarray) -> np.ndarray:
        if self.config.dither_mode == "none":
            return luminance

        bayer = np.array(
            [
                [0, 8, 2, 10],
                [12, 4, 14, 6],
                [3, 11, 1, 9],
                [15, 7, 13, 5],
            ],
            dtype=np.float32,
        )
        threshold = ((bayer + 0.5) / 16.0 - 0.5) * (255.0 / len(self._ascii_lut))
        tiled = np.resize(threshold, luminance.shape)
        return np.clip(luminance + tiled, 0, 255)

    @staticmethod
    def _ascii_matrix_to_text(char_matrix: np.ndarray) -> str:
        return "\n".join("".join(row) for row in char_matrix)

    @staticmethod
    def _ascii_matrix_to_truecolor_text(char_matrix: np.ndarray, frame_bgr: np.ndarray) -> str:
        frame_rgb = frame_bgr[:, :, ::-1].astype(np.uint8, copy=False)
        lines = []

        for char_row, color_row in zip(char_matrix, frame_rgb, strict=True):
            cells = [
                f"\033[38;2;{red};{green};{blue}m{char}"
                for char, (red, green, blue) in zip(char_row, color_row, strict=True)
            ]
            lines.append("".join(cells) + ANSI_RESET)

        return "\n".join(lines)

    @staticmethod
    def _ascii_matrix_to_256color_text(char_matrix: np.ndarray, frame_bgr: np.ndarray) -> str:
        frame_rgb = frame_bgr[:, :, ::-1].astype(np.uint8, copy=False)
        levels = np.clip(np.rint(frame_rgb.astype(np.float32) / 255.0 * 5), 0, 5).astype(np.uint8)
        color_indexes = 16 + (36 * levels[:, :, 0]) + (6 * levels[:, :, 1]) + levels[:, :, 2]
        lines = []

        for char_row, color_row in zip(char_matrix, color_indexes, strict=True):
            cells = [
                f"\033[38;5;{int(color_index)}m{char}"
                for char, color_index in zip(char_row, color_row, strict=True)
            ]
            lines.append("".join(cells) + ANSI_RESET)

        return "\n".join(lines)

    @staticmethod
    def _ascii_matrix_to_grayscale_text(char_matrix: np.ndarray, luminance: np.ndarray) -> str:
        gray_indexes = 232 + np.clip(
            np.rint(np.clip(luminance, 0, 255) / 255.0 * 23),
            0,
            23,
        ).astype(np.uint8)
        lines = []

        for char_row, color_row in zip(char_matrix, gray_indexes, strict=True):
            cells = [
                f"\033[38;5;{int(color_index)}m{char}"
                for char, color_index in zip(char_row, color_row, strict=True)
            ]
            lines.append("".join(cells) + ANSI_RESET)

        return "\n".join(lines)
