from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from ascii_motion.frame_processor import FrameProcessor, FrameProcessorConfig

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "demo" / "ascii-motion-demo.gif"
FRAME_COUNT = 42
SOURCE_SIZE = (160, 90)
ASCII_WIDTH = 74
ASCII_HEIGHT = 28
CANVAS_SIZE = (980, 600)
FONT_SIZE = 12


def make_source_frame(index: int) -> np.ndarray:
    width, height = SOURCE_SIZE
    frame = np.zeros((height, width, 3), dtype=np.uint8)

    x_gradient = np.linspace(20, 180, width, dtype=np.uint8)
    y_gradient = np.linspace(10, 90, height, dtype=np.uint8)
    frame[:, :, 0] = x_gradient
    frame[:, :, 1] = y_gradient[:, None]
    frame[:, :, 2] = 34

    phase = index / FRAME_COUNT
    center_x = int((0.5 + 0.34 * np.sin(phase * np.pi * 2)) * width)
    center_y = int((0.5 + 0.24 * np.cos(phase * np.pi * 2)) * height)
    radius = int(18 + 8 * np.sin(phase * np.pi * 4))

    cv2.circle(frame, (center_x, center_y), radius, (60, 240, 135), -1)
    cv2.circle(frame, (width - center_x, height - center_y), 14, (225, 190, 70), -1)
    cv2.line(
        frame,
        (0, int(height * phase)),
        (width, int(height * (1 - phase))),
        (90, 220, 240),
        3,
    )
    return frame


def load_font() -> ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Menlo.ttc",
        "/System/Library/Fonts/Monaco.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, FONT_SIZE)
    return ImageFont.load_default()


def draw_terminal(ascii_frame: str, frame_index: int, font: ImageFont.ImageFont) -> Image.Image:
    image = Image.new("RGB", CANVAS_SIZE, "#070908")
    draw = ImageDraw.Draw(image)

    shell = (54, 48, CANVAS_SIZE[0] - 54, CANVAS_SIZE[1] - 48)
    draw.rounded_rectangle(shell, radius=8, fill="#101613", outline="#355342", width=2)
    draw.rectangle((shell[0], shell[1], shell[2], shell[1] + 46), fill="#151f19")

    for offset, color in enumerate(("#ff6f61", "#ffc857", "#8dffb1")):
        x = shell[0] + 22 + (offset * 18)
        draw.ellipse((x, shell[1] + 18, x + 10, shell[1] + 28), fill=color)

    draw.text(
        (shell[0] + 92, shell[1] + 17),
        "ghostty · zsh · ascii-motion",
        fill="#aab9af",
        font=font,
    )
    draw.rounded_rectangle(
        (shell[2] - 94, shell[1] + 13, shell[2] - 20, shell[1] + 33),
        radius=10,
        outline="#6ee7f2",
        width=1,
    )
    draw.text((shell[2] - 78, shell[1] + 17), "30 FPS", fill="#6ee7f2", font=font)

    draw.text(
        (shell[0] + 22, shell[1] + 62),
        "$ ascii-motion demo.mp4 --width 74 --color truecolor",
        fill="#ffc857",
        font=font,
    )

    y = shell[1] + 92
    for line in ascii_frame.splitlines():
        draw.text((shell[0] + 22, y), line, fill="#8dffb1", font=font)
        y += FONT_SIZE + 2

    cursor_visible = (frame_index // 4) % 2 == 0
    if cursor_visible:
        draw.rectangle((shell[0] + 22, y + 6, shell[0] + 32, y + 16), fill="#8dffb1")

    draw.text(
        (shell[0] + 22, shell[3] - 34),
        "q quit · space pause · arrows seek · vectorized luminance",
        fill="#708077",
        font=font,
    )

    return image


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    font = load_font()
    processor = FrameProcessor(
        FrameProcessorConfig(width=ASCII_WIDTH, height=ASCII_HEIGHT, ascii_chars=" .:-=+*#%@")
    )

    frames = [
        draw_terminal(processor.process(make_source_frame(index)), index, font)
        for index in range(FRAME_COUNT)
    ]
    frames[0].save(
        OUTPUT,
        save_all=True,
        append_images=frames[1:],
        duration=64,
        loop=0,
        optimize=True,
    )
    print(OUTPUT)


if __name__ == "__main__":
    main()
