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
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'isa')))

from isa_types import UInt64, Vec4x64
from register_file import register_file

class WriteBackStage:
    def __init__(self, register_file: register_file):
        self.rf = register_file
        self.metrics = {
            'writebacks': 0,
            'cycles': 0,
            'special_writes': 0
        }
    
    def execute(self, mem_result, decoded_instr):
        """
        Ejecuta etapa WB - CORREGIDO
        """
        result = mem_result.get('result')
        rd = decoded_instr['operandos'].get('rd')
        opcode = decoded_instr['opcode_name']
        
        print(f"🔧 WB: result={result}, rd={rd}, opcode={opcode}")
        
        written = False
        if result is not None and rd is not None:
            # CORRECCIÓN: Escribir en el registro destino
            reg_name = f"R{rd}"
            print(f"📝 Escribiendo {result} en {reg_name}")
            self.rf.write(reg_name, result)
            self.metrics['writebacks'] += 1
            written = True
        
        self.metrics['cycles'] += 1
        
        return {
            'written': written,
            'register': rd,
            'value': result
        }
    
    def get_metrics(self):
        return dict(self.metrics)