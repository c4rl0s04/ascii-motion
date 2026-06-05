from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
DOCS_DEMO_DIR = ROOT / "docs" / "demo"
SITE_ASSETS_DIR = ROOT / "site" / "assets"
DOCS_GIF = DOCS_DEMO_DIR / "ascii-motion-demo.gif"
DOCS_MP4 = DOCS_DEMO_DIR / "ascii-motion-demo.mp4"
SITE_GIF = SITE_ASSETS_DIR / "ascii-motion-demo.gif"
SITE_MP4 = SITE_ASSETS_DIR / "ascii-motion-demo.mp4"
SITE_POSTER = SITE_ASSETS_DIR / "ascii-motion-demo-poster.png"
FRAME_COUNT = 42
FPS = 16
SOURCE_SIZE = (160, 90)
ASCII_WIDTH = 74
ASCII_HEIGHT = 28
CANVAS_SIZE = (980, 600)
FONT_SIZE = 12


def make_source_frame(index: int) -> Image.Image:
    width, height = SOURCE_SIZE
    frame = np.zeros((height, width, 3), dtype=np.uint8)

    x_gradient = np.linspace(20, 180, width, dtype=np.uint8)
    y_gradient = np.linspace(10, 90, height, dtype=np.uint8)
    frame[:, :, 0] = 34
    frame[:, :, 1] = y_gradient[:, None]
    frame[:, :, 2] = x_gradient

    phase = index / FRAME_COUNT
    center_x = int((0.5 + 0.34 * np.sin(phase * np.pi * 2)) * width)
    center_y = int((0.5 + 0.24 * np.cos(phase * np.pi * 2)) * height)
    radius = int(18 + 8 * np.sin(phase * np.pi * 4))

    image = Image.fromarray(frame, "RGB")
    draw = ImageDraw.Draw(image)
    draw.ellipse(
        (center_x - radius, center_y - radius, center_x + radius, center_y + radius),
        fill=(135, 240, 60),
    )
    draw.ellipse(
        (
            width - center_x - 14,
            height - center_y - 14,
            width - center_x + 14,
            height - center_y + 14,
        ),
        fill=(70, 190, 225),
    )
    draw.line(
        (0, int(height * phase), width, int(height * (1 - phase))),
        fill=(240, 220, 90),
        width=3,
    )
    return image


def process_ascii(source: Image.Image) -> str:
    resized = source.resize((ASCII_WIDTH, ASCII_HEIGHT), Image.Resampling.BOX)
    rgb = np.asarray(resized, dtype=np.float32)
    luminance = (0.2126 * rgb[:, :, 0]) + (0.7152 * rgb[:, :, 1]) + (0.0722 * rgb[:, :, 2])
    chars = np.asarray(list(" .:-=+*#%@"))
    indices = np.clip((luminance / 255.0 * (len(chars) - 1)).astype(np.intp), 0, len(chars) - 1)
    ascii_matrix = chars[indices]
    return "\n".join("".join(row) for row in ascii_matrix)


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


def save_gif(frames: list[Image.Image], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        output,
        save_all=True,
        append_images=frames[1:],
        duration=int(1000 / FPS),
        loop=0,
        optimize=False,
    )


def save_mp4(frames: list[Image.Image], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("ffmpeg is required to generate the documentation MP4 asset.")

    with tempfile.TemporaryDirectory(prefix="ascii-motion-demo-") as temp_dir:
        temp_path = Path(temp_dir)
        for index, frame in enumerate(frames):
            frame.save(temp_path / f"frame-{index:04d}.png")

        subprocess.run(
            [
                ffmpeg,
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-framerate",
                str(FPS),
                "-i",
                str(temp_path / "frame-%04d.png"),
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                str(output),
            ],
            check=True,
        )


def main() -> None:
    DOCS_DEMO_DIR.mkdir(parents=True, exist_ok=True)
    SITE_ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    font = load_font()

    frames = [
        draw_terminal(process_ascii(make_source_frame(index)), index, font)
        for index in range(FRAME_COUNT)
    ]
    save_gif(frames, DOCS_GIF)
    save_mp4(frames, DOCS_MP4)
    frames[0].save(SITE_POSTER)
    shutil.copyfile(DOCS_GIF, SITE_GIF)
    shutil.copyfile(DOCS_MP4, SITE_MP4)

    for output in (DOCS_GIF, DOCS_MP4, SITE_GIF, SITE_MP4, SITE_POSTER):
        print(output)


if __name__ == "__main__":
    main()
