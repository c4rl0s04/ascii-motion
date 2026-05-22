from __future__ import annotations

import argparse
import sys
import time
from collections.abc import Sequence
from pathlib import Path

from . import __version__
from .benchmark import BenchmarkStats
from .charsets import CHARSETS, DEFAULT_CHARSET_NAME
from .frame_processor import FrameProcessor, FrameProcessorConfig
from .keyboard import (
    ACTION_BACKWARD,
    ACTION_FORWARD,
    ACTION_HELP,
    ACTION_PAUSE,
    ACTION_QUIT,
    KeyboardController,
)
from .stream_manager import FrameClock, StreamManager
from .terminal_renderer import PlaybackStatus, TerminalRenderer

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
        choices=("none", "truecolor", "256", "grayscale"),
        default="none",
        help="Modo de color ANSI. Por defecto no aplica color.",
    )
    parser.add_argument(
        "--mode",
        choices=("ascii", "edges", "hybrid"),
        default="ascii",
        help="Modo de procesamiento visual.",
    )
    parser.add_argument(
        "--dither",
        choices=("none", "ordered"),
        default="none",
        help="Modo de dithering aplicado antes del mapeo ASCII.",
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
    parser.add_argument("--no-hud", action="store_true", help="Oculta el HUD de reproduccion.")
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Oculta la barra de progreso de reproduccion.",
    )
    parser.add_argument(
        "--show-controls",
        action="store_true",
        help="Muestra la ayuda de controles desde el inicio.",
    )
    parser.add_argument(
        "--real-time",
        action="store_true",
        help="Salta frames si el renderizado va tarde para mantener tiempo real.",
    )
    parser.add_argument("--preview", action="store_true", help="Muestra metadatos y termina.")
    parser.add_argument(
        "--frame-at",
        type=non_negative_float,
        default=None,
        help="Renderiza un unico frame en el segundo indicado y termina.",
    )
    parser.add_argument("--export", default=None, help="Exporta una animacion ASCII a texto.")
    parser.add_argument(
        "--export-ansi",
        default=None,
        help="Exporta una animacion ANSI reproducible en terminal.",
    )
    parser.add_argument(
        "--export-frames",
        default=None,
        help="Exporta frames ASCII numerados al directorio indicado.",
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
        "--help-key",
        type=single_character,
        default="?",
        help="Tecla para mostrar u ocultar controles. Por defecto: ?.",
    )
    parser.add_argument(
        "--seek-seconds",
        type=positive_float,
        default=5.0,
        help="Segundos que avanza o retrocede cada salto. Por defecto: 5.",
    )
    return parser.parse_args(argv)


def build_processor_config(
    args: argparse.Namespace,
    reserved_rows: int = 0,
) -> FrameProcessorConfig:
    size = TerminalRenderer.terminal_size()
    width = args.width or size.columns
    height = args.height
    max_height = None

    if args.fit_terminal:
        width = args.width or size.columns
        height = args.height or max(1, size.rows - reserved_rows)
    elif args.width is None and args.height is None:
        max_height = max(1, size.rows - reserved_rows)

    return FrameProcessorConfig(
        width=width,
        height=height,
        max_height=max_height,
        ascii_chars=resolve_ascii_chars(args.charset, args.chars),
        invert=args.invert,
        color_mode=args.color,
        processor_mode=args.mode,
        dither_mode=args.dither,
    )


def print_benchmark(stats: BenchmarkStats) -> None:
    print(
        "Benchmark: "
        f"frames={stats.frame_count}, "
        f"skipped={stats.skipped_frames}, "
        f"elapsed={stats.elapsed_seconds:.3f}s, "
        f"effective_fps={stats.effective_fps:.2f}, "
        f"process_avg={stats.average_process_ms:.3f}ms, "
        f"render_avg={stats.average_render_ms:.3f}ms, "
        f"real_time={stats.real_time}",
        file=sys.stderr,
    )


def validate_output_mode(args: argparse.Namespace) -> None:
    modes = [
        args.preview,
        args.frame_at is not None,
        args.export is not None,
        args.export_ansi is not None,
        args.export_frames is not None,
    ]
    if sum(bool(mode) for mode in modes) > 1:
        raise ValueError("Solo puedes usar un modo de salida no interactivo a la vez.")


def show_hud(args: argparse.Namespace) -> bool:
    return not args.no_hud


def show_progress(args: argparse.Namespace, total_seconds: float | None) -> bool:
    return not args.no_progress and total_seconds is not None


def reserved_rows(
    args: argparse.Namespace,
    controls_visible: bool,
    total_seconds: float | None,
) -> int:
    return TerminalRenderer.reserved_rows(
        show_hud=show_hud(args),
        show_progress=show_progress(args, total_seconds),
        show_controls=controls_visible,
    )


def playback_status(
    args: argparse.Namespace,
    stream: StreamManager,
    processor: FrameProcessor,
    stats: BenchmarkStats,
    target_fps: float,
    paused: bool,
    output_width: int,
    output_height: int,
) -> PlaybackStatus:
    return PlaybackStatus(
        current_seconds=stream.current_seconds(),
        total_seconds=stream.metadata.duration_seconds,
        effective_fps=stats.effective_fps,
        target_fps=target_fps,
        width=output_width,
        height=processor.config.height or output_height,
        paused=paused,
        color_mode=args.color,
        processor_mode=args.mode,
        skipped_frames=stats.skipped_frames,
    )


def maybe_rebuild_processor(
    args: argparse.Namespace,
    processor: FrameProcessor,
    controls_visible: bool,
    total_seconds: float | None,
) -> FrameProcessor:
    if not args.fit_terminal:
        return processor

    config = build_processor_config(args, reserved_rows(args, controls_visible, total_seconds))
    if config == processor.config:
        return processor

    return FrameProcessor(config)


def print_preview(
    args: argparse.Namespace,
    stream: StreamManager,
    processor: FrameProcessor,
) -> None:
    duration = stream.metadata.duration_seconds
    print(f"source={args.source}")
    print(f"source_size={stream.metadata.width}x{stream.metadata.height}")
    print(f"source_fps={stream.metadata.fps:.3f}")
    print(f"source_frames={stream.metadata.frame_count}")
    print(f"duration={duration:.3f}s" if duration is not None else "duration=unknown")
    print(f"target_size={processor.config.width}x{processor.config.height or 'auto'}")
    print(f"target_fps={(args.fps or stream.metadata.fps):.3f}")
    print(f"charset={args.charset}")
    print(f"mode={args.mode}")
    print(f"dither={args.dither}")
    print(f"color={args.color}")


def frame_stride(source_fps: float, target_fps: float) -> int:
    if target_fps >= source_fps:
        return 1
    return max(1, round(source_fps / target_fps))


def iter_export_frames(
    args: argparse.Namespace,
    stream: StreamManager,
    processor: FrameProcessor,
) -> Sequence[str]:
    target_fps = args.fps or stream.metadata.fps
    stride = frame_stride(stream.metadata.fps, target_fps)
    deadline = None if args.duration is None else args.start + args.duration
    frames: list[str] = []

    stream.seek(args.start)
    for index, frame in enumerate(stream.frames()):
        if deadline is not None and stream.current_seconds() > deadline:
            break
        if index % stride != 0:
            continue
        frames.append(processor.process(frame))

    return frames


def run_non_interactive(args: argparse.Namespace) -> int:
    StreamManager.validate_file_source(args.source)
    processor = FrameProcessor(build_processor_config(args))

    with StreamManager(args.source, loop=False) as stream:
        if args.preview:
            print_preview(args, stream, processor)
            return 0

        if args.frame_at is not None:
            stream.seek(args.frame_at)
            try:
                frame = next(stream.frames())
            except StopIteration:
                raise ValueError("No se pudo leer un frame en el segundo indicado.") from None
            print(processor.process(frame))
            return 0

        frames = iter_export_frames(args, stream, processor)
        if args.export is not None:
            Path(args.export).write_text("\f".join(frames), encoding="utf-8")
        elif args.export_ansi is not None:
            content = TerminalRenderer.CLEAR_SCREEN + TerminalRenderer.CURSOR_HOME
            content += ("\n" + TerminalRenderer.CURSOR_HOME).join(frames)
            Path(args.export_ansi).write_text(content, encoding="utf-8")
        elif args.export_frames is not None:
            output_dir = Path(args.export_frames)
            output_dir.mkdir(parents=True, exist_ok=True)
            for index, frame_text in enumerate(frames):
                (output_dir / f"frame_{index:06d}.txt").write_text(frame_text, encoding="utf-8")

    return 0


def run(args: argparse.Namespace) -> int:
    validate_output_mode(args)

    if args.list_charsets:
        print(format_charsets())
        return 0

    if args.source is None:
        raise ValueError("Debes indicar una ruta de video o indice de camara.")

    if (
        args.preview
        or args.frame_at is not None
        or args.export is not None
        or args.export_ansi is not None
        or args.export_frames is not None
    ):
        return run_non_interactive(args)

    StreamManager.validate_file_source(args.source)
    stats = BenchmarkStats()
    stats.real_time = args.real_time

    with StreamManager(args.source, loop=args.loop) as stream:
        processor = FrameProcessor(
            build_processor_config(
                args,
                reserved_rows(args, args.show_controls, stream.metadata.duration_seconds),
            )
        )
        stream.seek(args.start)
        target_fps = args.fps or stream.metadata.fps
        clock = FrameClock(target_fps)
        deadline = None if args.duration is None else time.perf_counter() + args.duration

        stats.start()
        with (
            KeyboardController(
                quit_key=args.quit_key,
                pause_key=args.pause_key,
                backward_key=args.backward_key,
                forward_key=args.forward_key,
                help_key=args.help_key,
            ) as keyboard,
            TerminalRenderer(use_alt_screen=not args.no_alt_screen) as renderer,
        ):
            frames = stream.frames()
            paused = False
            paused_at: float | None = None
            controls_visible = args.show_controls

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
                elif action == ACTION_HELP:
                    controls_visible = not controls_visible

                processor = maybe_rebuild_processor(
                    args,
                    processor,
                    controls_visible,
                    stream.metadata.duration_seconds,
                )

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
                renderer.render(
                    ascii_frame,
                    status=playback_status(
                        args,
                        stream,
                        processor,
                        stats,
                        target_fps,
                        paused,
                        max((len(line) for line in ascii_frame.splitlines()), default=0),
                        ascii_frame.count("\n") + 1,
                    ),
                    show_hud=show_hud(args),
                    show_progress=show_progress(args, stream.metadata.duration_seconds),
                    show_controls=controls_visible,
                )
                stats.render_seconds += time.perf_counter() - render_started

                stats.frame_count += 1
                clock.wait_next_frame()
                if args.real_time and not paused:
                    skipped = stream.skip_frames(clock.frames_to_skip())
                    stats.skipped_frames += skipped
                    clock.advance(skipped)
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
