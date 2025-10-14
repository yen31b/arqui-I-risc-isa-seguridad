# txt2hex.py
"""
Convierte un archivo .txt (salida del assembler) a .hex y devuelve lista de enteros.
No depende del pipeline.
"""

HEX_PREFIX = "0x"
WORD_BITS = 32
WORD_MAX = (1 << WORD_BITS) - 1

def _clean_line(line: str) -> str:
    for sep in (';', '#'):
        if sep in line:
            line = line.split(sep, 1)[0]
    return line.strip()

def _parse_int_auto(line: str) -> int:
    s = line.lower()
    if s.startswith("0x"):
        return int(s, 16)
    if all(ch in ("0", "1") for ch in s):
        return int(s, 2)
    return int(s.split()[0], 10)

def _to_hex32(value: int) -> str:
    masked = value & WORD_MAX
    return f"{HEX_PREFIX}{masked:08x}"

def convert_txt_to_hex(input_txt: str, output_hex: str | None = None) -> list[int]:
    ints: list[int] = []
    hex_lines: list[str] = []

    with open(input_txt, "r", encoding="utf-8") as f:
        for raw in f:
            line = _clean_line(raw)
            if not line:
                continue
            value = _parse_int_auto(line)
            if not (0 <= value <= WORD_MAX):
                raise ValueError(f"Valor fuera de rango de 32 bits: {value}")
            ints.append(value)
            hex_lines.append(_to_hex32(value))

    if output_hex:
        with open(output_hex, "w", encoding="utf-8") as f:
            for h in hex_lines:
                f.write(h + "\n")

    return ints
