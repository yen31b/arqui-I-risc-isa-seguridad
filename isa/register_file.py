"""
register_file.py

Banco de registros para la CPU Toy:
 - 32 registros generales nombrados 'R0'..'R31'
 - Registros especiales: PC, SR
 - Todos los valores se almacenan como UInt64 (máscara automática aplicable).
Notas de diseño:
 - La implementación actual permite escribir en R0 para mantener compatibilidad
   con tests y herramientas de desarrollo. En una ISA real R0 sería invariantes.
 - dump_registers() devuelve un diccionario de enteros (útil para tests y logs).
"""

from isa_types import UInt64
from isa_definition import REGISTERS_DECISION

class register_file:
    """
    Modelo de banco de registros para CPU de propósito criptográfico.
    Usa REGISTERS_DECISION como fuente de verdad para número de registros,
    ancho y nombre del zero register.
    """

    def __init__(self):
        # Obtener parámetros desde la definición centralizada
        general_count = REGISTERS_DECISION.get('general_count', 32)
        self._zero_register = REGISTERS_DECISION.get('zero_register', 'R0')
        self._mask = (1 << REGISTERS_DECISION.get('general_width_bits', 64)) - 1

        # Registros generales: R0–R{N-1}, inicializados a 0 como UInt64
        self.general = {f'R{i}': UInt64(0) for i in range(general_count)}

        # Registros especiales
        self.PC = UInt64(0)  # Program Counter
        self.SR = UInt64(0)  # Status Register

    def read(self, name):
        """
        Lee el valor de un registro por nombre; retorna UInt64.
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
        - Aplica máscara definida por REGISTERS_DECISION.
        - Convierte y almacena como UInt64.
        - Nota: por compatibilidad con pruebas actuales, no se bloquea la escritura
          sobre el zero_register; si se desea cambiar esto a futuro, se puede
          elevar una excepción aquí.
        """
        ival = int(value) & self._mask  # aplica máscara basada en la decisión global

        # Nota: se permite escribir en el zero register para mantener compatibilidad
        # con las pruebas existentes que esperan poder escribir/leer R0.

        if name in self.general:
            self.general[name] = UInt64(ival)
        elif name == 'PC':
            self.PC = UInt64(ival)
        elif name == 'SR':
            self.SR = UInt64(ival)
        else:
            raise ValueError(f"Registro inválido: {name}")

    def dump_registers(self):
        """
        Retorna un diccionario con el estado actual de todos los registros.
        Formato:
            { 'R0': int, 'R1': int, ..., 'PC': int, 'SR': int }
        Útil para serializar/depurar sin imprimir directamente.
        """
        result = {name: int(self.general[name]) for name in sorted(self.general.keys())}
        result['PC'] = int(self.PC)
        result['SR'] = int(self.SR)
        return result

    @property
    def registers(self):
        """Propiedad de conveniencia que retorna snapshot de registros (dump_registers)."""
        return self.dump_registers()
