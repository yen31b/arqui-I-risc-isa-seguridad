"""
vault.py

Implementación única y centralizada de la Bóveda (KeyVault).
Responsabilidades:
 - Almacenar slots definidos en isa_definition.VAULT_SLOTS como valores UInt64.
 - Proveer acceso controlado y atómico a las llaves via access_slot_for_operation.
 - Generar firmas atómicas con generate_signature sin exponer la llave.
Seguridad:
 - Sólo operaciones autorizadas (KVL, KVOP, SGEN) pueden acceder a los slots.
 - dump_vault() está protegido por un flag 'authorized' y retorna enteros
   (o None) para facilitar logging/depuración.
"""
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'isa')))

from typing import Dict
from isa_types import UInt64, Vec4x64
from isa_definition import VAULT_SLOTS

class VaultAccessError(Exception):
    pass

class KeyVault:
    def __init__(self):
        # Inicializar todos los slots como None
        self._slots: Dict[str, UInt64] = {name: None for name in VAULT_SLOTS.keys()}
        # Contadores de auditoría
        self._counters = {'reads': 0, 'writes': 0, 'ops': 0}

    def _mask64(self, v):
        return UInt64(int(v) & 0xFFFFFFFFFFFFFFFF)

    def write_slot(self, slot_name: str, value: int, authorized: bool = False):
        """
        Escribir un valor en la bóveda.
        authorized debe ser True si la escritura viene de instrucción KVW autorizada.
        """
        if slot_name not in self._slots:
            raise VaultAccessError(f"Slot inválido: {slot_name}")

        if not authorized:
            raise VaultAccessError("Escritura en bóveda prohibida: contexto no autorizado")

        self._slots[slot_name] = self._mask64(value)
        self._counters['writes'] += 1

    def access_slot_for_operation(self, slot_name: str, operation: str) -> UInt64:
        """
        Acceso controlado a un slot para operaciones permitidas (KVL, KVOP, SGEN).
        Retorna el valor UInt64 para uso interno en la operación atómica.
        """
        if slot_name not in self._slots:
            raise VaultAccessError(f"Slot inválido: {slot_name}")

        if self._slots[slot_name] is None:
            raise VaultAccessError(f"Slot {slot_name} no inicializado")

        # Permitir acceso solo desde operaciones especiales (simulado por nombre)
        allowed_ops = {'KVL', 'KVOP', 'SGEN'}
        if operation not in allowed_ops:
            raise VaultAccessError(f"Operación '{operation}' no permitida para leer bóveda")

        # Incrementar contadores y devolver el UInt64 interno (uso atómico simulado)
        self._counters['reads'] += 1
        self._counters['ops'] += 1
        return self._slots[slot_name]

    def generate_signature(self, slot_name: str, state: Vec4x64) -> Vec4x64:
        """
        Genera la firma S = state XOR K usando la llave almacenada en slot_name.
        La llave no se expone; se pasa como UInt64 a la función de la unidad funcional.
        """
        key = self.access_slot_for_operation(slot_name, 'SGEN')
        # state.xor_with_key acepta UInt64/int y devuelve Vec4x64
        return state.xor_with_key(key)

    def get_audit_counters(self):
        return dict(self._counters)

    def dump_vault(self, authorized: bool = False):
        """
        Mostrar estado de la bóveda para depuración.
        - authorized: True obliga a la llamada a tener permiso explícito.
        - Retorna { slot_name: int | None }
        """
        if not authorized:
            raise VaultAccessError("Dump de bóveda requiere autorización")
        # devolver enteros para facilidad de impresión/serialización
        return {k: (int(v) if v is not None else None) for k, v in self._slots.items()}
