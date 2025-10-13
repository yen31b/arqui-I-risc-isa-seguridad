# loader.py

import tkinter as tk
from tkinter import filedialog
import os

def select_file():
    """Abre una ventana para seleccionar un archivo local."""
    root = tk.Tk()
    root.withdraw()  # Oculta la ventana principal
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
    aplica padding si es necesario, imprime los bloques y los devuelve.
    """
    if path is None:
        path = select_file()

    with open(path, "rb") as f:
        data = f.read()

    original_size = len(data)
    padding = (8 - (original_size % 8)) % 8
    if padding:
        data += b'\x00' * padding
        print(f"[Loader] Se aplicaron {padding} bytes de padding.")

    blocks = [
        int.from_bytes(data[i:i+8], byteorder='big')
        for i in range(0, len(data), 8)
    ]

    print(f"[Loader] Total de bloques de 64 bits: {len(blocks)}")
    print("[Loader] Contenido de los bloques:")
    for i, block in enumerate(blocks):
        print(f"  Bloque {i:04d} → {block:016X}")

    return blocks

# Ejecución directa (opcional)
if __name__ == "__main__":
    load_file_to_blocks()
