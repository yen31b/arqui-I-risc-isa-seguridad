# vault_interface.py

"""
Interfaz entre la bóveda y el pipeline.
Responsabilidad:
 - Coordinar operaciones atómicas con la bóveda
 - Generar señales de control de seguridad
 - Validar integridad de operaciones
"""
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'isa')))

from vault import KeyVault, VaultAccessError
from isa_types import UInt64, Vec4x64

class VaultInterface:
    def __init__(self):
        self.vault = KeyVault()
        self.security_metrics = {
            'vault_ops': 0,
            'security_violations': 0,
            'atomic_operations': 0
        }
    
    def generate_control_signals(self, opcode, operands):
        """
        Genera señales de control para operaciones con bóveda
        """
        signals = {
            'vault_op': False,
            'needs_authorization': False,
            'atomic_operation': False,
            'slot_index': None
        }
        
        vault_ops = ['VSTORE', 'VINIT', 'SIGN', 'KVL', 'KVOP']
        if opcode in vault_ops:
            signals['vault_op'] = True
            signals['needs_authorization'] = True
            signals['atomic_operation'] = opcode in ['SIGN', 'KVOP']
            signals['slot_index'] = operands.get('vault_idx')
        
        return signals
    
    def execute_vault_operation(self, operation, slot_idx, **kwargs):
        """
        Ejecuta operación atómica con la bóveda - VERSIÓN CORREGIDA
        """
        try:
            slot_name = self._index_to_slot(slot_idx)
            
            if operation == 'KVW':
                value = kwargs.get('value', 0)
                self.vault.write_slot(slot_name, value, authorized=True)
                result = None
            
            elif operation == 'KVL':
                result = self.vault.access_slot_for_operation(slot_name, 'KVL')
            
            elif operation == 'KVOP':
                result = self.vault.access_slot_for_operation(slot_name, 'KVOP')
            
            elif operation == 'SGEN':
                state = kwargs.get('state')
                if not isinstance(state, Vec4x64):
                    raise ValueError("Se requiere Vec4x64 para generación de firma")
                result = self.vault.generate_signature(slot_name, state)
            
            else:
                raise ValueError(f"Operación de bóveda no soportada: {operation}")
            
            self.security_metrics['vault_ops'] += 1
            if operation in ['SGEN', 'KVOP']:
                self.security_metrics['atomic_operations'] += 1
            
            return result
            
        except Exception as e:
            # CONTAR CUALQUIER EXCEPCIÓN como violación de seguridad
            self.security_metrics['security_violations'] += 1
            
            # Relanzar la excepción original
            if isinstance(e, (VaultAccessError, ValueError)):
                raise e
            else:
                # Para otros tipos de errores, envolver en VaultAccessError
                raise VaultAccessError(f"Error en operación de bóveda: {e}")
    
    def _index_to_slot(self, index):
        """Convierte índice numérico a nombre de slot - VERSIÓN CORREGIDA"""
        slots = ['KEY_0', 'KEY_1', 'KEY_2', 'KEY_3', 
                'HASH_A', 'HASH_B', 'HASH_C', 'HASH_D']
        
        # Validar que el índice esté en rango
        if index is None or index < 0 or index >= len(slots):
            raise ValueError(f"Índice de bóveda inválido: {index}")
        
        return slots[index]
    
    def get_security_report(self):
        """Reporte de seguridad y métricas"""
        vault_counters = self.vault.get_audit_counters()
        return {
            **self.security_metrics,
            'vault_reads': vault_counters['reads'],
            'vault_writes': vault_counters['writes'],
            'vault_operations': vault_counters['ops']
        }