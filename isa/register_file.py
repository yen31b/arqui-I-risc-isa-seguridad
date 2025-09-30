
class register_file:
    """
    Modelo de banco de registros para CPU de propósito criptográfico.
    Incluye 32 registros generales de 64 bits, PC y SR.
    """

    def __init__(self):
        # Registros generales: R0–R31
        self.general = {f'R{i}': 0 for i in range(32)}

        # Registros especiales
        self.PC = 0  # Program Counter
        self.SR = 0  # Status Register

    def read(self, name):
        """
        Lee el valor de un registro por nombre.
        """
        if name in self.general:
            return self.general[name]
        elif name == 'PC':
            return self.PC
        elif name == 'SR':
            return self.SR
        else:
            raise ValueError(f"Registro inválido: {name}")

    def write(self, name, value):
        """
        Escribe un valor en el registro especificado.
        Aplica máscara de 64 bits.
        """
        masked_value = value & 0xFFFFFFFFFFFFFFFF  # Asegura 64 bits

        if name in self.general:
            self.general[name] = masked_value
        elif name == 'PC':
            self.PC = masked_value
        elif name == 'SR':
            self.SR = masked_value
        else:
            raise ValueError(f"Registro inválido: {name}")

    def dump_registers(self):
        """
        Imprime el estado actual de todos los registros.
        """
        print("=== ESTADO DE REGISTROS ===")
        for name in sorted(self.general.keys()):
            print(f"{name}: {self.general[name]:016X}")
        print(f"PC : {self.PC:016X}")
        print(f"SR : {self.SR:016X}")
