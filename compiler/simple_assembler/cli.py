"""CLI minimalista para el ensamblador sencillo."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable, Sequence

from .assembler import Assembler, AssemblyError, format_words


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ensamblador simple RISC de 32 bits")
    parser.add_argument("source", help="Archivo .asm de entrada o '-' para stdin")
    parser.add_argument("-o", "--output", help="Archivo de salida (binario textual)")
    parser.add_argument(
        "-f",
        "--format",
        choices=("bin", "hex", "int"),
        default="bin",
        help="Formato de salida (bin, hex, int)",
    )
    parser.add_argument(
        "--emit-address",
        action="store_true",
        help="Incluye dirección base + offset en cada línea",
    )
    parser.add_argument(
        "--base-address",
        type=lambda x: int(x, 0),
        default=0,
        help="Dirección base para anotaciones (--emit-address)",
    )
    return parser


def read_source(token: str) -> str:
    if token == "-":
        return sys.stdin.read()
    return Path(token).read_text(encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    assembler = Assembler()
    try:
        source = read_source(args.source)
        words = assembler.assemble(source)
    except FileNotFoundError:
        parser.error(f"No se encontró el archivo '{args.source}'")
    except AssemblyError as exc:
        print(exc, file=sys.stderr)
        return 1

    formatted = format_words(words, fmt=args.format)
    if args.emit_address:
        formatted = [f"0x{args.base_address + idx:08X}: {value}" for idx, value in enumerate(formatted)]
    output_text = "\n".join(formatted)
    if output_text:
        output_text += "\n"

    if args.output:
        Path(args.output).write_text(output_text, encoding="utf-8")
    else:
        sys.stdout.write(output_text)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
