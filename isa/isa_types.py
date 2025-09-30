
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


class Vec4x64:
    """
    Vector de 4 enteros de 64 bits (256 bits totales).
    Usado para representar el estado hash ToyMDMA: (A, B, C, D).
    """

    def __init__(self, a, b, c, d):
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
        Aplica XOR entre cada componente y una llave UInt64.
        Retorna nuevo Vec4x64.
        """
        return Vec4x64(*(v ^ UInt64(key) for v in self.values))
