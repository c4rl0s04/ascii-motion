from __future__ import annotations

import argparse
import sys
import time
from collections.abc import Sequence

from . import __version__
from .benchmark import BenchmarkStats
from .charsets import CHARSETS, DEFAULT_CHARSET_NAME
from .frame_processor import FrameProcessor, FrameProcessorConfig
from .keyboard import (
    ACTION_BACKWARD,
    ACTION_FORWARD,
    ACTION_PAUSE,
    ACTION_QUIT,
    KeyboardController,
)
from .stream_manager import FrameClock, StreamManager
from .terminal_renderer import TerminalRenderer

PAUSE_POLL_SECONDS = 0.03


def positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("debe ser mayor que cero")
    return parsed


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("debe ser mayor que cero")
    return parsed


def non_negative_float(value: str) -> float:
    parsed = float(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("no puede ser negativo")
    return parsed


def single_character(value: str) -> str:
    if len(value) != 1:
        raise argparse.ArgumentTypeError("debe ser un unico caracter")
    return value


def resolve_ascii_chars(charset: str, chars: str | None) -> str:
    if charset == "custom":
        if chars is None:
            raise ValueError("--charset custom requiere --chars.")
        resolved = chars
    elif chars is not None:
        resolved = chars
    else:
        resolved = CHARSETS[charset]

    if len(resolved) < 2:
        raise ValueError("La escala ASCII debe contener al menos dos caracteres.")

    return resolved


def format_charsets() -> str:
    lines = ["Available charsets:"]
    for name, chars in CHARSETS.items():
        preview = chars.replace(" ", "·")
        lines.append(f"  {name:<7} {preview}")
    lines.append("  custom  use --charset custom --chars \"...\"")
    return "\n".join(lines)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="ascii-motion",
        description="Reproduce videos como animaciones ASCII en la terminal.",
    )
    parser.add_argument(
        "source",
        nargs="?",
        help="Ruta del video o indice de camara, por ejemplo: 0",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "--list-charsets",
        action="store_true",
        help="Lista las escalas ASCII disponibles y termina.",
    )
    parser.add_argument(
        "-w",
        "--width",
        type=positive_int,
        default=None,
        help="Columnas ASCII objetivo. Por defecto usa el ancho actual de la terminal.",
    )
    parser.add_argument(
        "--height",
        type=positive_int,
        default=None,
        help="Filas ASCII objetivo. Si se omite, se calcula preservando aspecto visual.",
    )
    parser.add_argument(
        "--fps",
        type=positive_float,
        default=None,
        help="FPS de reproduccion. Si se omite, usa el FPS reportado por el video.",
    )
    parser.add_argument(
        "--fit-terminal",
        action="store_true",
        help="Ajusta ancho y alto al tamano actual de la terminal.",
    )
    parser.add_argument(
        "--no-alt-screen",
        action="store_true",
        help="No usa la pantalla alternativa ANSI.",
    )
    parser.add_argument(
        "--charset",
        choices=(*CHARSETS.keys(), "custom"),
        default=DEFAULT_CHARSET_NAME,
        help="Escala predefinida de caracteres.",
    )
    parser.add_argument(
        "--chars",
        default=None,
        help="Escala personalizada de caracteres de oscuro a claro.",
    )
    parser.add_argument("--invert", action="store_true", help="Invierte la escala ASCII.")
    parser.add_argument(
        "--color",
        choices=("none", "truecolor"),
        default="none",
        help="Modo de color ANSI. Por defecto no aplica color.",
    )
    parser.add_argument("--loop", action="store_true", help="Reproduce el video en bucle.")
    parser.add_argument(
        "--start",
        type=non_negative_float,
        default=0.0,
        help="Segundo inicial de reproduccion.",
    )
    parser.add_argument(
        "--duration",
        type=positive_float,
        default=None,
        help="Duracion maxima de reproduccion en segundos.",
    )
    parser.add_argument(
        "--benchmark",
        action="store_true",
        help="Muestra metricas de rendimiento al terminar.",
    )
    parser.add_argument(
        "--quit-key",
        type=single_character,
        default="q",
        help="Tecla para salir durante la reproduccion. Por defecto: q.",
    )
    parser.add_argument(
        "--pause-key",
        type=single_character,
        default=" ",
        help="Tecla para pausar o reanudar. Por defecto: espacio.",
    )
    parser.add_argument(
        "--backward-key",
        type=single_character,
        default="h",
        help="Tecla para retroceder durante la reproduccion. Por defecto: h.",
    )
    parser.add_argument(
        "--forward-key",
        type=single_character,
        default="l",
        help="Tecla para avanzar durante la reproduccion. Por defecto: l.",
    )
    parser.add_argument(
        "--seek-seconds",
        type=positive_float,
        default=5.0,
        help="Segundos que avanza o retrocede cada salto. Por defecto: 5.",
    )
    return parser.parse_args(argv)


def build_processor_config(args: argparse.Namespace) -> FrameProcessorConfig:
    size = TerminalRenderer.terminal_size()
    width = args.width or size.columns
    height = args.height

    if args.fit_terminal:
        width = args.width or size.columns
        height = args.height or max(1, size.rows - 1)

    return FrameProcessorConfig(
        width=width,
        height=height,
        ascii_chars=resolve_ascii_chars(args.charset, args.chars),
        invert=args.invert,
        color_mode=args.color,
    )


def print_benchmark(stats: BenchmarkStats) -> None:
    print(
        "Benchmark: "
        f"frames={stats.frame_count}, "
        f"elapsed={stats.elapsed_seconds:.3f}s, "
        f"effective_fps={stats.effective_fps:.2f}, "
        f"process_avg={stats.average_process_ms:.3f}ms, "
        f"render_avg={stats.average_render_ms:.3f}ms",
        file=sys.stderr,
    )


def run(args: argparse.Namespace) -> int:
    if args.list_charsets:
        print(format_charsets())
        return 0

    if args.source is None:
        raise ValueError("Debes indicar una ruta de video o indice de camara.")

    StreamManager.validate_file_source(args.source)
    processor = FrameProcessor(build_processor_config(args))
    stats = BenchmarkStats()

    with StreamManager(args.source, loop=args.loop) as stream:
        stream.seek(args.start)
        clock = FrameClock(args.fps or stream.metadata.fps)
        deadline = None if args.duration is None else time.perf_counter() + args.duration

        stats.start()
        with (
            KeyboardController(
                quit_key=args.quit_key,
                pause_key=args.pause_key,
                backward_key=args.backward_key,
                forward_key=args.forward_key,
            ) as keyboard,
            TerminalRenderer(use_alt_screen=not args.no_alt_screen) as renderer,
        ):
            frames = stream.frames()
            paused = False
            paused_at: float | None = None

            while True:
                action = keyboard.read_action()
                if action == ACTION_QUIT:
                    break
                if action == ACTION_PAUSE:
                    paused = not paused
                    if paused:
                        paused_at = time.perf_counter()
                    else:
                        if deadline is not None and paused_at is not None:
                            deadline += time.perf_counter() - paused_at
                        paused_at = None
                        clock.reset()
                elif action == ACTION_BACKWARD:
                    stream.seek_relative(-args.seek_seconds)
                    clock.reset()
                elif action == ACTION_FORWARD:
                    stream.seek_relative(args.seek_seconds)
                    clock.reset()

                if paused:
                    time.sleep(PAUSE_POLL_SECONDS)
                    continue

                if deadline is not None and time.perf_counter() >= deadline:
                    break

                try:
                    frame = next(frames)
                except StopIteration:
                    break

                process_started = time.perf_counter()
                ascii_frame = processor.process(frame)
                stats.process_seconds += time.perf_counter() - process_started

                render_started = time.perf_counter()
                renderer.render(ascii_frame)
                stats.render_seconds += time.perf_counter() - render_started

                stats.frame_count += 1
                clock.wait_next_frame()
        stats.finish()

    if args.benchmark:
        print_benchmark(stats)

    return 0


def main(argv: Sequence[str] | None = None) -> int:
    try:
        return run(parse_args(argv))
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
