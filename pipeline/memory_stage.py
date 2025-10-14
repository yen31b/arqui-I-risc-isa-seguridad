# memory_stage.py

"""
Etapa MEM (Memory Access) del pipeline.
Responsabilidad:
 - Acceder a memoria general (LOAD/STORE)
 - Bloquear accesos a rango de bóveda
 - Interactuar con la bóveda para operaciones KV*
 - Recolectar métricas de seguridad
"""
from vault.vault_interface import VaultInterface
from isa.isa_types import UInt64, Vec4x64

# Boot image global para precargar DataMemory al inicio del Pipeline.
# Formato: dict[int_address] = int_value (64 bits)
BOOT_IMAGE: dict[int, int] | None = None

def set_boot_image(image: dict[int, int]) -> None:
    """Configura una imagen de arranque global que será copiada a cada DataMemory nueva."""
    global BOOT_IMAGE
    # almacenar copia inmutable (por seguridad)
    BOOT_IMAGE = {int(k): int(v) for k, v in image.items()}

class DataMemory:
    def __init__(self, size=1024, vault_range=(0x1000, 0x1FFF)):
        self.memory = {}
        self.vault_range = vault_range
        self.metrics = {
            'mem_accesses': 0,
            'vault_accesses': 0,
            'security_blocks': 0
        }
        # Precargar boot image si existe (evita validación de rango aquí; se asume segura)
        if BOOT_IMAGE:
            # Cargar valores como enteros 64b
            for addr, val in BOOT_IMAGE.items():
                self.memory[int(addr)] = int(val)
            print(f"[DataMemory] Boot image precargada: {len(BOOT_IMAGE)} entradas.")
    
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
    def __init__(self, data_memory: DataMemory, vault_if: VaultInterface | None = None):
        self.mem = data_memory
        self.vault_if = vault_if
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
        
        # Si la instrucción requiere acceso a la bóveda, delegar a VaultInterface
        if ctrl.get('use_boveda', False):
            if not self.vault_if:
                raise RuntimeError("VaultInterface no configurada en MemoryStage para acceso a bóveda")

            slot_idx = ops.get('vault_idx')

            # Si EX ya ejecutó la operación de bóveda (vault_signal), NO re-ejecutar aquí.
            if ex_result.get('vault_signal'):
                # EX ya interactuó con la bóveda; tomar resultado y latencia de EX
                result = ex_result.get('result')
                latency = ex_result.get('latency', 1)
                print(f"  🔧 MEM: Operación de bóveda ya ejecutada en EX (skip MEM). slot={slot_idx} result={result}")
                # No incrementamos vault_accesses en DataMemory porque la ejecución fue en EX
            else:
                # Contabilizar acceso a bóveda en métricas de DataMemory (vista global)
                try:
                    self.mem.metrics['vault_accesses'] = self.mem.metrics.get('vault_accesses', 0) + 1
                except Exception:
                    pass

                try:
                    # Dependiendo de la instrucción, el EX ya pudo devolver un resultado (p.ej. state)
                    if opcode in ('KVL', 'VLOAD'):
                        result = self.vault_if.execute_vault_operation('KVL', slot_idx)
                    elif opcode in ('KVW', 'VSTORE', 'VINIT'):
                        # value puede venir de operandos o de ex_result
                        value = ops.get('rs2_val', ex_result.get('result'), ops.get('rs1_val'))
                        self.vault_if.execute_vault_operation('KVW', slot_idx, value=value)
                        result = None
                    elif opcode in ('SGEN', 'SIGN', 'KVOP'):
                        # usar el resultado de EX (por ejemplo el estado hash) o los operandos
                        state = ex_result.get('result') or ops.get('hash_state')
                        result = self.vault_if.execute_vault_operation('SGEN' if opcode in ('SGEN','SIGN') else 'KVOP', slot_idx, state=state, value=ops.get('rs1_val'))
                    else:
                        # delegar genérico
                        result = self.vault_if.execute_vault_operation(opcode, slot_idx, value=ex_result.get('result'))
                    latency = ex_result.get('latency', 1) + 1
                    print(f"  🔧 MEM: Bóveda {opcode} slot={slot_idx} result={result}")
                except Exception as e:
                    # contabilizar y propagar
                    self.metrics['operations'] += 1
                    self.metrics['cycles'] += 1
                    raise

        # Caso: operaciones con memoria
        else:
            # Caso: operaciones con memoria general
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