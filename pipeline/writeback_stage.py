# writeback_stage.py

"""
Etapa WB (Write Back) del pipeline.
Responsabilidad:
 - Escribir resultados en registros destino
 - Manejar resultados especiales (firmas, estados hash)
 - Recolectar métricas de escritura
"""
import sys
import os
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', 'isa')))

from isa_types import UInt64, Vec4x64
from register_file import register_file

class WriteBackStage:
    def __init__(self, register_file: register_file):
        self.rf = register_file
        self.metrics = {
            'writebacks': 0,
            'cycles': 0,
            'special_writes': 0  # Para firmas, estados hash, etc.
        }
    
    def execute(self, mem_result, decoded_instr):
        """
        Ejecuta etapa WB
        mem_result: resultado de etapa MEM
        decoded_instr: instrucción decodificada
        """
        result = mem_result.get('result')
        rd = decoded_instr['operandos'].get('rd')
        opcode = decoded_instr['opcode_name']
        
        if result is not None and rd is not None:
            # Escritura normal a registro
            self.rf.write(f'R{rd}', result)
            self.metrics['writebacks'] += 1
        
        elif isinstance(result, Vec4x64):
            # Escritura de firma/estado hash a registros múltiples
            self._write_vector_result(result, rd)
            self.metrics['special_writes'] += 1
        
        self.metrics['cycles'] += 1
        
        return {
            'written': result is not None,
            'register': rd,
            'value': result
        }
    
    def _write_vector_result(self, vector: Vec4x64, base_reg):
        """
        Escribe un vector de 4x64 bits en registros consecutivos
        Ej: R{base_reg}←A, R{base_reg+1}←B, etc.
        """
        if base_reg is not None:
            for i, value in enumerate(vector.values):
                reg_name = f'R{(base_reg + i) % 32}'  # Wrap around 32 registros
                self.rf.write(reg_name, value)
    
    def get_metrics(self):
        return dict(self.metrics)