# loader.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..','..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'pipeline')))

import tkinter as tk
from tkinter import filedialog
import os
from typing import List, Tuple, Optional
from isa.isa_definition import VAULT_ADDR_RANGE
from pipeline.memory_stage import set_boot_image  # para registrar boot image global

def select_file():
    """Abre una ventana para seleccionar un archivo local."""
    root = tk.Tk()
    root.withdraw()  # Oculta la ventana principal de Tkinter
    file_path = filedialog.askopenfilename(
        title="Selecciona un archivo para procesar",
        filetypes=[("Todos los archivos", "*.*")]
    )
    if not file_path:
        raise FileNotFoundError("No se seleccionó ningún archivo.")
    print(f"\n[Loader] Archivo seleccionado: {os.path.basename(file_path)}")
    return file_path

def load_file_to_blocks(path=None):
    """
    Carga un archivo binario, lo divide en bloques de 64 bits (8 bytes),
    aplica padding si es necesario, y devuelve un listado de 'palabras'
    de 64 bits donde la posición 0 es el conteo de bloques y el resto
    son los bloques.
    """
    if path is None:
        path = select_file()

    with open(path, "rb") as f:
        data = f.read()

    size         = len(data)
    padding      = (8 - (size % 8)) % 8
    if padding:
        data += b'\x00' * padding
        print(f"[Loader] Se aplicaron {padding} bytes de padding.")

    # Partimos en bloques de 8 bytes → enteros 64 bits
    blocks = [
        int.from_bytes(data[i : i+8], byteorder='big')
        for i in range(0, len(data), 8)
    ]
    count   = len(blocks)

    # Construimos la 'memoria': [count, block0, block1, …]
    mem_data = [count] + blocks

    # Impresión empírica
    print(f"[Loader] Total de bloques = {count}")
    print("[Loader] Memoria de datos simulada (dir : valor 64 bits):")
    for addr, word in enumerate(mem_data):
        print(f"  {addr:04d} : 0x{word:016X}")
    print(mem_data)
    return mem_data

def _bytes_to_blocks(data: bytes, *, endian: str = "big") -> List[int]:
    """Convierte bytes en una lista de enteros de 64 bits (8 bytes por bloque)."""
    blocks: List[int] = []
    for i in range(0, len(data), 8):
        word = int.from_bytes(data[i:i+8], byteorder=endian, signed=False)
        blocks.append(word)
    return blocks

def _choose_safe_blocks_base(count: int, *, header_base: int, vault_range: Tuple[int, int]) -> int:
    """
    Elige una base segura para los bloques evitando VAULT_ADDR_RANGE.
    Layout propuesto:
      header_base:    count (64b)
      header_base+8:  blocks_base (puntero a primer bloque)
      blocks_base:    block0, block1, ...
    """
    vault_lo, vault_hi = vault_range
    # Intento preferido: bloques inmediatamente después del header (header_base+16)
    tentative_base = header_base + 16
    last_addr = tentative_base + (count - 1) * 8 if count > 0 else tentative_base
    # Si no interseca con bóveda, usarlo
    if not (tentative_base <= vault_hi and last_addr >= vault_lo):
        return tentative_base
    # Si interseca, mover bloques a justo después del rango de bóveda
    safe_base = ((vault_hi + 8) // 8) * 8  # alinea a 8
    return safe_base

def _build_boot_image_from_bytes(data: bytes, *, header_base: int = 0, endian: str = "big") -> dict[int, int]:
    """
    Construye un diccionario {addr: value64} con:
      - header_base      -> count
      - header_base + 8  -> blocks_base
      - blocks_base + i*8-> block[i]
    Evita VAULT_ADDR_RANGE reubicando blocks_base (e incluso header si fuese necesario).
    """
    # Padding y bloques
    pad = (8 - (len(data) % 8)) % 8
    if pad:
        data += b"\x00" * pad
        print(f"[Loader] Se aplicaron {pad} bytes de padding.")
    blocks = _bytes_to_blocks(data, endian=endian)
    count = len(blocks)

    # Elegir base segura para bloques
    blocks_base = _choose_safe_blocks_base(count, header_base=header_base, vault_range=VAULT_ADDR_RANGE)
    expected_base = header_base + 16

    # Si header cae en rango de bóveda, reubicar header y bloques juntos
    vault_lo, vault_hi = VAULT_ADDR_RANGE
    if vault_lo <= header_base <= vault_hi or vault_lo <= (header_base + 8) <= vault_hi:
        header_base = ((vault_hi + 8) // 8) * 8
        blocks_base = header_base + 16
        print(f"[Loader] Header reubicado fuera de VAULT_ADDR_RANGE a 0x{header_base:04x}.")

    if blocks_base != expected_base:
        print(f"[Loader] Bloques reubicados fuera de VAULT_ADDR_RANGE {VAULT_ADDR_RANGE}: "
              f"blocks_base=0x{blocks_base:04x} (header_base=0x{header_base:04x})")

    # Construir imagen
    image: dict[int, int] = {}
    image[header_base] = count
    image[header_base + 8] = blocks_base
    for i, w in enumerate(blocks):
        addr = blocks_base + i * 8
        # Evitar solapar con bóveda por si acaso
        if vault_lo <= addr <= vault_hi:
            # Reubicar todo si esta comprobación falla (muy improbable por cómputo previo)
            raise RuntimeError(f"Dirección de bloque cae en VAULT_ADDR_RANGE: 0x{addr:04x}")
        image[addr] = w
    return image

def load_file_into_memory(
    data_memory,
    path: Optional[str] = None,
    *,
    header_base: int = 0,
    blocks_base: Optional[int] = None,
    endian: str = "big",
) -> dict:
    """
    Carga un archivo binario y escribe:
      - count en header_base
      - blocks_base (puntero) en header_base+8
      - cada bloque de 64 bits desde blocks_base, en pasos de 8 bytes
    Respeta VAULT_ADDR_RANGE reubicando blocks_base si fuese necesario.
    Retorna {'header_base': int, 'blocks_base': int, 'count': int}
    """
    if path is None:
        path = select_file()
    with open(path, "rb") as f:
        data = f.read()

    # Padding a múltiplos de 8
    padding = (8 - (len(data) % 8)) % 8
    if padding:
        data += b"\x00" * padding
        print(f"[Loader] Se aplicaron {padding} bytes de padding.")

    blocks = _bytes_to_blocks(data, endian=endian)
    count = len(blocks)

    # Elegir base de bloques segura si no se especificó
    chosen_blocks_base = blocks_base if blocks_base is not None else _choose_safe_blocks_base(
        count, header_base=header_base, vault_range=VAULT_ADDR_RANGE
    )

    # Advertir si se reubicó respecto del layout contiguo (header+16)
    expected_base = header_base + 16
    if chosen_blocks_base != expected_base:
        print(f"[Loader] Bloques reubicados fuera de VAULT_ADDR_RANGE {VAULT_ADDR_RANGE}: "
              f"blocks_base=0x{chosen_blocks_base:04x} (header_base=0x{header_base:04x})")

    # Escribir en DataMemory usando su API (valida VAULT_ADDR_RANGE)
    # Header
    try:
        data_memory.write(header_base, count)
        data_memory.write(header_base + 8, chosen_blocks_base)
    except PermissionError as e:
        # Si por alguna razón el header cae en VAULT_ADDR_RANGE, mover header fuera también
        header_base = ((VAULT_ADDR_RANGE[1] + 8) // 8) * 8
        expected_base = header_base + 16
        chosen_blocks_base = expected_base
        print(f"[Loader] Header reubicado a 0x{header_base:04x} por restricción de bóveda. "
              f"Nuevo blocks_base=0x{chosen_blocks_base:04x}")
        data_memory.write(header_base, count)
        data_memory.write(header_base + 8, chosen_blocks_base)

    # Bloques
    for i, word in enumerate(blocks):
        addr = chosen_blocks_base + i * 8
        data_memory.write(addr, word)

    print(f"[Loader] Cargados {count} bloques en DataMemory. "
          f"header=0x{header_base:04x}, blocks_base=0x{chosen_blocks_base:04x}")
    return {'header_base': header_base, 'blocks_base': chosen_blocks_base, 'count': count}

def assemble_and_load_into_datamemory(assembler, data_memory, asm_path: str, *, header_base: int = 0, endian: str = "big"):
    """
    Opción alternativa: ensamblar un .s a palabras de 64 bits (p.ej. mensajes empaquetados)
    y cargarlas como bloques en DataMemory usando el mismo layout (header+puntero+bloques).
    'assembler' debe proveer un método assemble_file que retorne lista de enteros de 32b o 64b.
    """
    words = assembler.assemble_file(asm_path)
    # Empaquetar de 2 en 2 a 64 bits (si son 32b)
    blocks: List[int] = []
    for i in range(0, len(words), 2):
        hi = words[i] & 0xFFFFFFFF
        lo = (words[i+1] & 0xFFFFFFFF) if (i + 1) < len(words) else 0
        blocks.append(((hi << 32) | lo) & 0xFFFFFFFFFFFFFFFF)
    # Escribir
    chosen_blocks_base = _choose_safe_blocks_base(len(blocks), header_base=header_base, vault_range=VAULT_ADDR_RANGE)
    data_memory.write(header_base, len(blocks))
    data_memory.write(header_base + 8, chosen_blocks_base)
    for i, w in enumerate(blocks):
        data_memory.write(chosen_blocks_base + i * 8, w)
    return {'header_base': header_base, 'blocks_base': chosen_blocks_base, 'count': len(blocks)}

if __name__ == "__main__":
    # Al ejecutarse: seleccionar archivo, construir boot image y registrarla globalmente.
    try:
        path = select_file()
        with open(path, "rb") as f:
            data = f.read()
        image = _build_boot_image_from_bytes(data, header_base=0, endian="big")
        set_boot_image(image)
        count = image.get(0, 0)
        blocks_base = image.get(8, 0)
        print(f"[Loader] Boot image registrada: count={count}, header=0x0000, blocks_base=0x{blocks_base:04x}")
        print("[Loader] Ahora puedes ejecutar el pipeline (ej.: python -m pipeline.run_main --asm Assembly\\hast.s --batch)")
    except Exception as e:
        print(f"[Loader] Error preparando boot image: {e}")
