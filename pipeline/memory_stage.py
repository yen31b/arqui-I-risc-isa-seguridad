# memory_stage.py

"""
Etapa MEM (Memory Access) del pipeline.
Responsabilidad:
 - Acceder a memoria general (LOAD/STORE)
 - Bloquear accesos a rango de bóveda
 - Interactuar con la bóveda para operaciones KV*
 - Recolectar métricas de seguridad
"""
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'isa')))

from isa_types import UInt64, Vec4x64

class DataMemory:
    def __init__(self, size=1024, vault_range=(0x1000, 0x1FFF)):
        self.memory = {}
        self.vault_range = vault_range
        self.metrics = {
            'mem_accesses': 0,
            'vault_accesses': 0,
            'security_blocks': 0
        }
    
    def validate_memory_access(self, address):
        """Valida que la dirección no esté en rango de bóveda"""
        addr = int(address)
        if self.vault_range[0] <= addr <= self.vault_range[1]:
            self.metrics['security_blocks'] += 1
            raise PermissionError(f"Acceso prohibido a rango de bóveda: 0x{addr:08x}")
        return True
    
    def read(self, address):
        """Lee de memoria general - CORREGIDO"""
        self.metrics['mem_accesses'] += 1
        self.validate_memory_access(address)
        addr_int = int(address)
        return UInt64(self.memory.get(addr_int, 0))
    
    def write(self, address, value):
        """Escribe en memoria general - CORREGIDO"""
        self.metrics['mem_accesses'] += 1
        self.validate_memory_access(address)
        addr_int = int(address)
        val_int = int(value) if hasattr(value, 'value') else int(value)
        self.memory[addr_int] = val_int
    
    def get_metrics(self):
        return dict(self.metrics)

class MemoryStage:
    def __init__(self, data_memory: DataMemory):
        self.mem = data_memory
        self.metrics = {'cycles': 0, 'operations': 0}
    
    def execute(self, ex_result, decoded_instr):
        """
        Ejecuta etapa MEM - CORREGIDO
        """
        result = None
        latency = 1
        
        opcode = decoded_instr['opcode_name']
        ops = decoded_instr.get('operandos', {})  # CORRECCIÓN: usar get() para evitar KeyError
        ctrl = decoded_instr['control_signals']
        
        print(f"  🔧 MEM: Opcode {opcode}, operandos: {list(ops.keys())}")
        
        # Caso: operaciones con memoria
        if opcode == 'LOAD':
            # Acceso a memoria general
            address = ex_result.get('result', 0)
            result = self.mem.read(address)
            latency = ex_result.get('latency', 1) + 1
            print(f"  🔧 MEM: LOAD desde 0x{int(address):x} = 0x{int(result):x}")
            
        elif opcode == 'STORE':
            # Escritura a memoria general
            address = ex_result.get('result', 0)
            value = ops.get('rs2_val', 0)  # CORRECCIÓN: en STORE, el valor está en rs2
            self.mem.write(address, value)
            result = None
            latency = ex_result.get('latency', 1) + 1
            print(f"  🔧 MEM: STORE 0x{int(value):x} en 0x{int(address):x}")

        else:
            # Instrucciones ALU / no-mem: propagar resultado de EX a WB
            result = ex_result.get('result')
            latency = ex_result.get('latency', 1)
            print(f"  🔧 MEM: Propagando resultado de EX: {result}")

        self.metrics['operations'] += 1
        self.metrics['cycles'] += latency
        
        return {
            'result': result,
            'latency': latency,
            'memory_accessed': opcode in ['LOAD', 'STORE'],
            'vault_accessed': ctrl.get('use_boveda', False)
        }
    
    def get_metrics(self):
        mem_metrics = self.mem.get_metrics()
        return {**self.metrics, **mem_metrics}