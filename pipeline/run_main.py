#!/usr/bin/env python3
"""
run_main.py

Uso típico:
  - Ensamblar ASM, cargar archivo binario a DataMemory y ejecutar en batch:
      python -m pipeline.run_main --asm Assembly\hast.s --data ruta\al\archivo.bin --batch

  - Ejecutar interactivo (sin datos):
      python -m pipeline.run_main --asm Assembly\test2.s

  - Cargar programa desde TXT (hex por línea) y correr batch:
      python -m pipeline.run_main --program programa.txt --batch

Notas:
  - --data usa loader.load_file_into_memory() y respeta VAULT_ADDR_RANGE.
  - Si ambos --asm y --program se pasan, se rechaza (elige uno).
"""

import argparse
import sys
from typing import List

from compiler.isa_assembler.assembler import Assembler
from compiler.isa_assembler.loader import load_file_into_memory
from compiler.isa_assembler.loader import dump_signed_file
from pipeline.pipeline import Pipeline

def parse_hex_program(path: str) -> List[int]:
    """
    Lee un archivo de texto con instrucciones en hex o int por línea y retorna lista de enteros (32b).
    Admite formatos como:
      - 0x1234abcd
      - 305419896
      - líneas vacías o comentarios se ignoran.
    """
    words: List[int] = []
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#") or line.startswith("//") or line.startswith(";"):
                continue
            # El CLI de assembler usualmente emite "0xXXXXXXXX" por línea
            try:
                if line.lower().startswith("0x"):
                    val = int(line, 16)
                else:
                    val = int(line, 0)
            except ValueError:
                print(f"[run_main] Línea ignorada (no numérica): {line}")
                continue
            words.append(val & 0xFFFFFFFF)
    if not words:
        raise ValueError(f"[run_main] No se encontraron instrucciones válidas en {path}")
    return words

def main():
    ap = argparse.ArgumentParser(description="Main runner: ensamblar/cargar y ejecutar el pipeline")
    gsrc = ap.add_mutually_exclusive_group(required=True)
    gsrc.add_argument("--asm", help="Ruta al archivo .s a ensamblar")
    gsrc.add_argument("--program", help="Ruta a programa .txt (hex por línea)")

    ap.add_argument("--data", help="Ruta a archivo binario para cargar en DataMemory (opcional)")
    ap.add_argument("--header-base", type=lambda x: int(x, 0), default=0, help="Dirección base del header para loader (por defecto 0)")
    ap.add_argument("--endian", choices=["big", "little"], default="big", help="Endian para bloques de datos (loader)")
    ap.add_argument("--batch", action="store_true", help="Ejecutar hasta el final sin modo interactivo")
    ap.add_argument("--verbose", action="store_true", help="Imprimir información adicional")
    ap.add_argument("--dump-signed-out", help="Ruta de salida para volcar archivo firmado (concat original+[hash]+firma)")

    args = ap.parse_args()

    # 1) Obtener instrucciones (assemble o leer hex)
    if args.asm:
        if args.verbose:
            print(f"[run_main] Ensamblando {args.asm} ...")
        words = Assembler().assemble_file(args.asm)
        if args.verbose:
            print(f"[run_main] Instrucciones ensambladas: {len(words)}")
    else:
        if args.verbose:
            print(f"[run_main] Cargando programa desde {args.program} ...")
        words = parse_hex_program(args.program)
        if args.verbose:
            print(f"[run_main] Instrucciones cargadas: {len(words)}")

    # 2) Crear pipeline
    p = Pipeline(words)

    # 3) Cargar archivo binario en DataMemory si se indicó --data
    if args.data:
        try:
            info = load_file_into_memory(
                p.data_mem,
                path=args.data,
                header_base=args.header_base,
                endian=args.endian,
            )
            print(f"[run_main] Datos cargados: count={info['count']}, header=0x{info['header_base']:04x}, blocks_base=0x{info['blocks_base']:04x}")
        except PermissionError as e:
            print(f"[run_main] ERROR: Acceso denegado al cargar datos en memoria: {e}")
            sys.exit(1)

    # 4) Ejecutar pipeline
    if args.batch:
        # Ejecutar hasta agotar instrucciones (sin modo interactivo)
        total = len(p.instr_mem.instructions)
        for _ in range(total):
            try:
                p.step()
            except IndexError:
                break
            except PermissionError as e:
                print(f"[run_main] 🛑 Violación de seguridad: {e}")
                break
            except Exception as e:
                print(f"[run_main] ❌ Error durante ejecución: {e}")
                break
        # Reporte final
        p._print_final_report()
    else:
        # Modo interactivo del pipeline
        p.run()

    # 5) (Opcional) Volcar archivo firmado a disco si se indicó
    if args.dump_signed_out:
        try:
            dump_signed_file(p.data_mem, args.dump_signed_out, header_base=args.header_base, endian=args.endian, include_hash=True)
        except Exception as e:
            print(f"[run_main] ⚠️ No se pudo volcar archivo firmado: {e}")

if __name__ == "__main__":
    main()
