"""CLI para el ensamblador oficial de la ISA."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from .assembler import Assembler, AssemblyError, format_words


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compila código ensamblador de la ISA a palabras de 32 bits")
    parser.add_argument("source", help="Archivo .asm de entrada o '-' para stdin")
    parser.add_argument("-o", "--output", help="Archivo de salida (texto)")
    parser.add_argument(
        "-f",
        "--format",
        choices=("hex", "bin", "int"),
        default="hex",
        help="Formato de representación de las palabras (hex por defecto)",
    )
    parser.add_argument(
        "--base-address",
        type=lambda value: int(value, 0),
        default=0,
        help="Dirección inicial (afecta cálculo de etiquetas)",
    )
    parser.add_argument(
        "--emit-address",
        action="store_true",
        help="Incluye columna con la dirección de cada palabra",
    )
    return parser


def read_source(token: str) -> str:
    if token == "-":
        return sys.stdin.read()
    return Path(token).read_text(encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    assembler = Assembler(base_address=args.base_address)
    try:
        source = read_source(args.source)
        words = assembler.assemble(source)
    except FileNotFoundError:
        parser.error(f"No se encuentra el archivo '{args.source}'")
    except AssemblyError as exc:
        print(exc, file=sys.stderr)
        return 1

    rendered = format_words(words, fmt=args.format)
    if args.emit_address:
        rendered = [f"0x{args.base_address + idx:08X}: {value}" for idx, value in enumerate(rendered)]
    output = "\n".join(rendered)
    if output:
        output += "\n"

    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    else:
        sys.stdout.write(output)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
