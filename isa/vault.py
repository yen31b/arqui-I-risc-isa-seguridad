"""
Key Vault (bóveda) model.
Provee API controlada: write_slot, access_slot_for_operation.
No expone lectura directa que pueda copiar llaves a registros/memoria.
"""
from typing import Dict
from isa_types import UInt64, Vec4x64
from isa_definition import VAULT_SLOTS

class VaultAccessError(Exception):
    pass

class KeyVault:
    def __init__(self):
        # Inicializar todos los slots a None
        self._slots: Dict[str, int] = {name: None for name in VAULT_SLOTS.keys()}
        # Contadores de auditoría
        self._counters = {'reads': 0, 'writes': 0, 'ops': 0}

    def _mask64(self, v):
        return UInt64(v & 0xFFFFFFFFFFFFFFFF)

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

    def access_slot_for_operation(self, slot_name: str, operation: str):
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

        # No se debe permitir que el llamador extraiga y guarde la llave en registro/memoria.
        # Aquí retornamos el valor para que la unidad funcional lo use atómicamente.
        self._counters['reads'] += 1
        self._counters['ops'] += 1
        return self._slots[slot_name]

    def generate_signature(self, slot_name: str, state: Vec4x64):
        """
        Genera la firma S = (A XOR K, B XOR K, C XOR K, D XOR K) usando la llave
        almacenada en slot_name. La llave no se devuelve ni se expone; la operación
        se realiza de forma atómica dentro de la bóveda (simulado).
        """
        # acceso controlado al slot para la operación atómica SGEN
        key = self.access_slot_for_operation(slot_name, 'SGEN')
        # state.xor_with_key retorna un Vec4x64 nuevo sin exponer la llave
        return state.xor_with_key(key)

    def get_audit_counters(self):
        return dict(self._counters)

    def dump_vault(self, authorized: bool = False):
        """
        Método de depuración: muestra estado de la bóveda solo si está autorizado.
        No usar en ejecución normal.
        """
        if not authorized:
            raise VaultAccessError("Dump de bóveda requiere autorización")
        return dict(self._slots)
