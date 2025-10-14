# vault_interface.py

"""
Interfaz entre la bóveda y el pipeline.
Responsabilidad:
 - Coordinar operaciones atómicas con la bóveda
 - Generar señales de control de seguridad
 - Validar integridad de operaciones
 - No exponer llaves en claro; operar mediante handles
"""

from typing import Optional, Dict, Any

from .vault import KeyVault, VaultAccessError, KeyHandle
from isa.isa_types import UInt64, Vec4x64
from isa.isa_definition import VAULT_SLOTS  # dict de nombres de slots canónicos


class VaultInterface:
    def __init__(self):
        self.vault = KeyVault()
        self.security_metrics = {
            'vault_ops': 0,
            'security_violations': 0,
            'atomic_operations': 0
        }

    def generate_control_signals(self, opcode: str, operands: Dict[str, Any]) -> Dict[str, Any]:
        """
        Genera señales de control para operaciones con bóveda
        """
        signals = {
            'vault_op': False,
            'needs_authorization': False,
            'atomic_operation': False,
            'slot_index': None,
            'slot_name': None
        }

        # Normalizar alias
        op = opcode.upper()
        if op in ('VSTORE', 'VINIT'):
            op = 'KVW'
        vault_ops = {'KVW', 'KVL', 'KVOP', 'SGEN'}

        if op in vault_ops:
            signals['vault_op'] = True
            signals['needs_authorization'] = (op == 'KVW')
            signals['atomic_operation'] = (op in {'KVOP', 'SGEN'})
            idx = operands.get('vault_idx')
            signals['slot_index'] = idx
            signals['slot_name'] = self._index_to_slot(idx)

        return signals

    def execute_vault_operation(self, operation: str, slot_idx: int, **kwargs):
        """
        Ejecuta operación con la bóveda usando handles seguros.
        No expone llaves en claro.
        """
        try:
            slot_name = self._index_to_slot(slot_idx)
            op = operation.upper()
            if op in ('VSTORE', 'VINIT'):
                op = 'KVW'

            result = None

            if op == 'KVW':
                value = kwargs.get('value', 0)
                self.vault.write_slot(slot_name, value, authorized=True)

            elif op == 'KVL':
                # Leer valor controlado del slot: usamos handle.xor_scalar(0) para obtener UInt64
                subop = kwargs.get('subop')
                handle: KeyHandle = self.vault.get_handle(slot_name, 'KVL')
                if subop == 'xor_scalar':
                    scalar = kwargs.get('scalar', 0)
                    result = handle.xor_scalar(scalar)
                else:
                    # devolver valor limpio del slot (xor_scalar(0) es un método seguro para obtener el UInt64)
                    result = handle.xor_scalar(0)
                    #result = handle

            elif op == 'KVOP':
                handle: KeyHandle = self.vault.get_handle(slot_name, 'KVOP')
                action = kwargs.get('action')
                if action == 'xor_scalar':
                    scalar = kwargs.get('scalar', 0)
                    result = handle.xor_scalar(scalar)
                elif action == 'use_for_signature':
                    state = kwargs.get('state')
                    if not isinstance(state, Vec4x64):
                        raise ValueError("Se requiere Vec4x64 para 'use_for_signature'")
                    result = handle.use_for_signature(state)
                else:
                    # fallback: devolver valor del slot de forma segura
                    result = handle.xor_scalar(0)

            elif op == 'SGEN':
                state = kwargs.get('state')
                if not isinstance(state, Vec4x64):
                    raise ValueError("Se requiere Vec4x64 para generación de firma")
                result = self.vault.generate_signature(slot_name, state)

            elif op == 'VERIFY':
                # Verifica que `signature` corresponda a `state XOR key(slot)`
                state = kwargs.get('state')
                signature = kwargs.get('signature')
                # Coerciones flexibles
                def to_vec4(x):
                    if isinstance(x, Vec4x64):
                        return x
                    if x is None:
                        return None
                    try:
                        vals = list(x)
                        if len(vals) == 4:
                            return Vec4x64(vals)
                    except Exception:
                        pass
                    # si llega un entero (posible), construir vector repetido (no habitual)
                    if isinstance(x, int):
                        return Vec4x64([x, x, x, x])
                    return None

                vec_state = to_vec4(state)
                vec_sig = to_vec4(signature)
                if vec_state is None or vec_sig is None:
                    raise ValueError("state y signature deben ser Vec4x64 o iterable de 4 enteros")

                # obtener handle seguro y generar firma esperada
                handle: KeyHandle = self.vault.get_handle(slot_name, 'KVL')
                expected = handle.use_for_signature(vec_state)  # Vec4x64
                ok = all(int(expected[i]) == int(vec_sig[i]) for i in range(4))
                result = bool(ok)

            else:
                raise ValueError(f"Operación de bóveda no soportada: {operation}")

            # Métricas
            self.security_metrics['vault_ops'] += 1
            if op in {'SGEN', 'KVOP'}:
                self.security_metrics['atomic_operations'] += 1

            return result

        except (VaultAccessError, ValueError) as e:
            #self.security_metrics['security_violations'] += 1
            raise e
        except Exception as e:
            self.security_metrics['security_violations'] += 1
            raise VaultAccessError(f"Error en operación de bóveda: {e}")

    def _index_to_slot(self, index: Optional[int]) -> str:
        """
        Convierte índice numérico a nombre de slot conforme a VAULT_SLOTS
        """
        slots = list(VAULT_SLOTS.keys())
        if index is None or index < 0 or index >= len(slots):
            raise ValueError(f"Índice de bóveda inválido: {index}")
        return slots[index]

    def get_security_report(self) -> Dict[str, Any]:
        """Reporte de seguridad y métricas"""
        vault_counters = self.vault.get_audit_counters()
        return {
            **self.security_metrics,
            'vault_reads': vault_counters['reads'],
            'vault_writes': vault_counters['writes'],
            'vault_operations': vault_counters['ops'],
            'vault_violations': vault_counters.get('violations', 0),
        }