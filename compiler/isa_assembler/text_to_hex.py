
# Pasa un doc txt a hex 
# las primeras 2 lineas del hex son la cant de bloques de 64 bits que hay en el doc txt

HEX_PREFIX = "0x"
WORD_BITS = 32
WORD_MAX = (1 << WORD_BITS) - 1

def _to_hex32(value: int) -> str:
    masked = value & WORD_MAX
    return f"{HEX_PREFIX}{masked:08x}"

def convert_txt_to_hex(input_txt: str, output_hex: str | None = None) -> list[int]:
    ints: list[int] = []
    hex_lines: list[str] = []

    # ✅ Leer TODO el archivo como texto completo, incluyendo \n
    with open(input_txt, "r", encoding="utf-8") as f:
        full_text = f.read()

    # ✅ Codificar a bytes (UTF-8), incluyendo saltos de línea
    bytes_data = full_text.encode("utf-8")

    # ✅ Convertir a bloques de 4 bytes → 32 bits
    for i in range(0, len(bytes_data), 4):
        chunk = bytes_data[i:i+4]
        value = 0
        for b in chunk:
            value = (value << 8) | b
        value <<= (4 - len(chunk)) * 8  # Padding a la izquierda si < 4 bytes
        ints.append(value)
        hex_lines.append(_to_hex32(value))

    # ✅ Asegurar que el total de palabras sea par (para formar bloques de 64 bits)
    if len(hex_lines) % 2 != 0:
        ints.append(0)
        hex_lines.append(_to_hex32(0))

    block_count = len(hex_lines) // 2

    if output_hex:
        with open(output_hex, "w", encoding="utf-8") as f:
            f.write(_to_hex32(block_count) + "\n")  # Línea 1: cantidad de bloques
            f.write(_to_hex32(0) + "\n")            # Línea 2: ceros
            for h in hex_lines:
                f.write(h + "\n")

    return ints
