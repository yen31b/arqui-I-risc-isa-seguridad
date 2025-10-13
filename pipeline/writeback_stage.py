# writeback_stage.py
"""
Etapa WB (Write Back) del pipeline.
Responsabilidad:
 - Escribir resultados en registros destino
 - Manejar resultados especiales (firmas, estados hash)
 - Recolectar métricas de escritura y seguridad
"""
from isa.isa_types import UInt64, Vec4x64
from isa.register_file import register_file

class WriteBackStage:
    def __init__(self, register_file: register_file):
        self.rf = register_file
        self.metrics = {
            'writebacks': 0,
            'cycles': 0,
            'special_writes': 0,
            'vault_write_violations': 0
        }
    
    def execute(self, mem_result, decoded_instr):
        """
        Ejecuta etapa WB con protecciones de seguridad
        """
        result = mem_result.get('result')
        rd = decoded_instr['operandos'].get('rd')
        opcode = decoded_instr['opcode_name']
        
        print(f"🔧 WB: result={result}, rd={rd}, opcode={opcode}")
        
        written = False
        if result is not None and rd is not None:
            reg_name = f"R{rd}"

            # 1. Bloquear si el valor proviene de la bóveda
            if hasattr(result, "_is_vault_secret") and getattr(result, "_is_vault_secret"):
                print(f"🛑 WB: Bloqueada escritura de valor secreto en {reg_name}")
                self.metrics['vault_write_violations'] += 1
                written = False
            # 2. Manejar resultados especiales (firmas, estados hash)
            elif isinstance(result, Vec4x64):
                print(f"📝 WB: Escritura especial (firma/hash) en {reg_name}..R{rd+3}")
                # Desempaquetar el vector en registros consecutivos
                components = list(result)  # Vec4x64 es iterable
                for i, comp in enumerate(components):
                    reg_i = f"R{rd + i}"
                    self.rf.write(reg_i, comp)
                    print(f"    → {reg_i} = {comp}")
                self.metrics['special_writes'] += 1
                self.metrics['writebacks'] += len(components)
                written = True
            # 3. Escritura normal
            else:
                print(f"📝 WB: Escribiendo {result} en {reg_name}")
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