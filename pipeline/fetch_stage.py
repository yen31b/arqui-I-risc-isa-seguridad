# fetch_stage.py

"""
Etapa IF (Instruction Fetch) del pipeline.
Responsabilidad:
 - Leer la instrucción desde memoria usando el PC.
 - Incrementar el PC.
 - Entregar la instrucción binaria a la etapa de decodificación.
"""
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'isa')))

from isa_definition import INSTRUCTION_FORMAT_DECISION
from register_file import register_file


class InstructionMemory:
    def __init__(self, instructions):
        """
        instructions: lista de enteros (cada uno representa una instrucción de 32 bits)
        """
        self.instructions = instructions

    def read(self, address):
        index = address // 4  # Asumiendo instrucciones de 4 bytes
        if 0 <= index < len(self.instructions):
            return self.instructions[index]
        else:
            raise IndexError(f"Dirección inválida de instrucción: {address}")


class FetchStage:
    def __init__(self, register_file: register_file, instr_mem: InstructionMemory):
        self.rf = register_file
        self.mem = instr_mem
        # bytes
        self.instr_size = INSTRUCTION_FORMAT_DECISION['width_bits'] // 8
        self.metrics = {'fetch_count': 0, 'cycles': 0}

    def step(self):
        """
        Ejecuta un ciclo de fetch:
         - Lee PC
         - Obtiene instrucción
         - Incrementa PC
         - Retorna instrucción binaria
        """
        pc = self.rf.read('PC')
        instr = self.mem.read(pc)
        self.rf.write('PC', pc + self.instr_size)

        self.metrics['fetch_count'] += 1
        self.metrics['cycles'] += 1

        return instr

    def get_metrics(self):
        return dict(self.metrics)
