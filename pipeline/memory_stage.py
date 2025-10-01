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
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', 'isa')))

from isa_types import UInt64
from vault import KeyVault, VaultAccessError

class DataMemory:
    def __init__(self, size=1024, vault_range=(0x1000, 0x1FFF)):
        """
        size: tamaño en bytes de memoria general
        vault_range: rango de direcciones reservado para bóveda (start, end)
        """
        self.memory = {}
        self.vault_range = vault_range
        self.vault = KeyVault()
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
        """Lee de memoria general"""
        self.metrics['mem_accesses'] += 1
        self.validate_memory_access(address)
        return self.memory.get(address, UInt64(0))
    
    def write(self, address, value):
        """Escribe en memoria general"""
        self.metrics['mem_accesses'] += 1
        self.validate_memory_access(address)
        self.memory[address] = UInt64(value)
    
    def vault_operation(self, operation, slot_name, value=None, state=None):
        """Operaciones seguras con la bóveda"""
        self.metrics['vault_accesses'] += 1
        try:
            if operation == 'KVW':  # Key Vault Write
                self.vault.write_slot(slot_name, value, authorized=True)
                return None
            elif operation == 'KVL':  # Key Vault Load
                return self.vault.access_slot_for_operation(slot_name, 'KVL')
            elif operation == 'KVOP':  # Key Vault Operation
                return self.vault.access_slot_for_operation(slot_name, 'KVOP')
            elif operation == 'SGEN':  # Signature Generation
                return self.vault.generate_signature(slot_name, state)
        except VaultAccessError as e:
            self.metrics['security_blocks'] += 1
            raise e
    
    def get_metrics(self):
        return dict(self.metrics)

class MemoryStage:
    def __init__(self, data_memory: DataMemory):
        self.mem = data_memory
        self.metrics = {'cycles': 0, 'operations': 0}
    
    def execute(self, ex_result, decoded_instr):
        """
        Ejecuta etapa MEM
        ex_result: resultado de etapa EX
        decoded_instr: instrucción decodificada
        """
        result = None
        latency = 1
        
        opcode = decoded_instr['opcode_name']
        ops = decoded_instr['operandos']
        ctrl = decoded_instr['control_signals']
        
        if ctrl['use_boveda']:
            # Operaciones con bóveda
            slot_name = self._get_slot_name(ops.get('vault_idx'))
            if opcode == 'VSTORE':
                value = ops.get('rs1_val', 0)
                self.mem.vault_operation('KVW', slot_name, value=value)
                result = None
            elif opcode == 'VINIT':
                key = ops.get('rs1_val', 0)
                self.mem.vault_operation('KVW', slot_name, value=key)
                result = None
            elif opcode == 'SIGN':
                state = ops.get('hash_state')
                if state:
                    signature = self.mem.vault_operation('SGEN', slot_name, state=state)
                    result = signature
                    latency = 3  # Operación criptográfica más lenta
            else:
                # KVL, KVOP
                result = self.mem.vault_operation('KVL', slot_name)
                latency = 2
        
        elif opcode == 'LOAD':
            # Acceso a memoria general
            address = ex_result.get('memory_address', 0)
            result = self.mem.read(address)
        
        elif opcode == 'STORE':
            # Escritura a memoria general
            address = ex_result.get('memory_address', 0)
            value = ops.get('rs1_val', 0)
            self.mem.write(address, value)
            result = None
        
        self.metrics['operations'] += 1
        self.metrics['cycles'] += latency
        
        return {
            'result': result,
            'latency': latency,
            'memory_accessed': opcode in ['LOAD', 'STORE'],
            'vault_accessed': ctrl['use_boveda']
        }
    
    def _get_slot_name(self, vault_idx):
        """Convierte índice de bóveda a nombre de slot"""
        slots = ['KEY_0', 'KEY_1', 'KEY_2', 'KEY_3', 
                'HASH_A', 'HASH_B', 'HASH_C', 'HASH_D']
        if 0 <= vault_idx < len(slots):
            return slots[vault_idx]
        raise ValueError(f"Índice de bóveda inválido: {vault_idx}")
    
    def get_metrics(self):
        mem_metrics = self.mem.get_metrics()
        return {**self.metrics, **mem_metrics}