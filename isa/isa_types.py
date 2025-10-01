"""
isa_types.py

Tipos básicos usados en el proyecto:
 - UInt64: entero sin signo de 64 bits (subclase de int) que aplica máscara.
 - Vec4x64: contenedor de 4 UInt64 (estado de hash A,B,C,D).
Detalles:
 - Vec4x64 acepta constructor flexible:
    * Vec4x64(a,b,c,d)
    * Vec4x64(iterable_of_4)
 - Las operaciones retornan instancias de estos tipos para consistencia.
"""

class UInt64(int):
    """
    Tipo entero sin signo de 64 bits.
    Aplica máscara automática para asegurar tamaño.
    """
    def __new__(cls, value):
        masked = value & 0xFFFFFFFFFFFFFFFF
        return int.__new__(cls, masked)

    def __repr__(self):
        return f"UInt64(0x{self:016X})"

    # Operaciones auxiliares útiles en varios stages
    def rotl(self, shift):
        """Rotate left over 64 bits."""
        s = int(shift) & 63
        val = (int(self) << s) & 0xFFFFFFFFFFFFFFFF
        val |= (int(self) >> (64 - s))
        return UInt64(val & 0xFFFFFFFFFFFFFFFF)

    def rotr(self, shift):
        """Rotate right over 64 bits."""
        s = int(shift) & 63
        val = (int(self) >> s) | ((int(self) << (64 - s)) & 0xFFFFFFFFFFFFFFFF)
        return UInt64(val & 0xFFFFFFFFFFFFFFFF)


class Vec4x64:
    """
    Vector de 4 enteros de 64 bits (256 bits totales).
    Usado para representar el estado hash ToyMDMA: (A, B, C, D).
    """

    def __init__(self, a, b=None, c=None, d=None):
        """
        Constructor flexible:
        - Vec4x64(a, b, c, d)
        - Vec4x64(iterable_of_4)
        """
        # Caso iterable único (p.ej. Vec4x64([a,b,c,d]) o Vec4x64((a,b,c,d)))
        if b is None and c is None and d is None:
            try:
                vals = list(a)
            except TypeError:
                raise TypeError("Vec4x64 requires either four positional values or a single iterable of length 4")
            if len(vals) != 4:
                raise TypeError("Iterable passed to Vec4x64 must have exactly 4 elements")
            self.values = [UInt64(v) for v in vals]
        else:
            # Caso cuatro argumentos posicionales
            self.values = [UInt64(a), UInt64(b), UInt64(c), UInt64(d)]

    def __getitem__(self, index):
        return self.values[index]

    def __setitem__(self, index, value):
        self.values[index] = UInt64(value)

    def __repr__(self):
        return ("Vec4x64([\n"
                f"  A: {self.values[0]},\n"
                f"  B: {self.values[1]},\n"
                f"  C: {self.values[2]},\n"
                f"  D: {self.values[3]}\n])")

    def xor_with_key(self, key):
        """
        XOR entre cada componente y la llave dada.
        - key puede ser UInt64 o entero.
        - Retorna un nuevo Vec4x64.
        """
        return Vec4x64(*(UInt64(int(v) ^ int(UInt64(key))) for v in self.values))
