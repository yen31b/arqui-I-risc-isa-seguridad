# vault.py
"""
Implementación central de la Bóveda (KeyVault) con handles seguros.
Responsabilidades:
 - Almacenar slots definidos en isa_definition.VAULT_SLOTS como UInt64.
 - Proveer acceso controlado mediante KeyHandle sin exponer la llave en claro.
 - Generar firmas atómicas con generate_signature.
Seguridad:
 - Sólo operaciones autorizadas (KVL, KVOP, SGEN) pueden usar handles.
 - write_slot requiere authorized=True.
 - dump_vault requiere authorized=True y nunca expone objetos internos.
Auditoría:
 - Contadores de reads/writes/ops/violations.
 - Cada intento inválido incrementa 'violations'.
"""
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'isa')))

from typing import Dict, Optional
from isa_types import UInt64, Vec4x64
from isa_definition import VAULT_SLOTS  # dict de slots definidos p.ej. {"K0": {}, "K1": {}}

class VaultAccessError(Exception):
    pass


class KeyHandle:
    """
    Handle seguro para operar con una llave sin exponer su valor.
    - No tiene métodos para leer la llave.
    - Sólo permite operaciones controladas (xor, derive, use_for_signature).
    """
    __slots__ = ("_kv", "_slot")

    def __init__(self, kv: "KeyVault", slot_name: str):
        self._kv = kv
        self._slot = slot_name

    def _get_key(self) -> UInt64:
        # Uso interno únicamente; no exponer fuera de Vault
        key = self._kv._get_slot_value(self._slot)
        if key is None:
            raise VaultAccessError(f"Slot {self._slot} no inicializado")
        return key

    def use_for_signature(self, state: Vec4x64) -> Vec4x64:
        # Operación atómica: state XOR key
        key = self._get_key()
        self._kv._counters["ops"] += 1
        return state.xor_with_key(key)

    # Ejemplo de operación derivada (opcional)
    def xor_scalar(self, value: int) -> UInt64:
        key = self._get_key()
        self._kv._counters["ops"] += 1
        return UInt64(int(key) ^ (int(value) & 0xFFFFFFFFFFFFFFFF))

    # Prohibir introspección
    def __int__(self):
        raise VaultAccessError("Lectura directa de llave prohibida")

    def __repr__(self):
        return f"<KeyHandle slot={self._slot}>"


class KeyVault:
    def __init__(self):
        # Inicializar todos los slots como None
        self._slots: Dict[str, Optional[UInt64]] = {name: None for name in VAULT_SLOTS.keys()}
        # Contadores de auditoría
        self._counters = {
            "reads": 0,
            "writes": 0,
            "ops": 0,
            "violations": 0,
        }

    def _mask64(self, v) -> UInt64:
        return UInt64(int(v) & 0xFFFFFFFFFFFFFFFF)

    def _get_slot_value(self, slot_name: str) -> Optional[UInt64]:
        return self._slots.get(slot_name, None)

    def write_slot(self, slot_name: str, value: int, authorized: bool = False):
        """
        Escribir un valor en la bóveda.
        authorized debe ser True si la escritura viene de una operación KVW autorizada.
        """
        if slot_name not in self._slots:
            self._counters["violations"] += 1
            raise VaultAccessError(f"Slot inválido: {slot_name}")

        if not authorized:
            self._counters["violations"] += 1
            raise VaultAccessError("Escritura en bóveda prohibida: contexto no autorizado")

        self._slots[slot_name] = self._mask64(value)
        self._counters["writes"] += 1

    def get_handle(self, slot_name: str, operation: str) -> KeyHandle:
        """
        Devuelve un handle seguro para operar con el slot.
        No expone la llave en claro; el handle sólo permite operaciones controladas.
        Operaciones permitidas: KVL, KVOP, SGEN.
        """
        if slot_name not in self._slots:
            self._counters["violations"] += 1
            raise VaultAccessError(f"Slot inválido: {slot_name}")

        if self._slots[slot_name] is None:
            self._counters["violations"] += 1
            raise VaultAccessError(f"Slot {slot_name} no inicializado")

        allowed_ops = {"KVL", "KVOP", "SGEN"}
        if operation not in allowed_ops:
            self._counters["violations"] += 1
            raise VaultAccessError(f"Operación '{operation}' no permitida para la bóveda")

        self._counters["reads"] += 1
        return KeyHandle(self, slot_name)

    def generate_signature(self, slot_name: str, state: Vec4x64) -> Vec4x64:
        """
        Genera firma atómica S = state XOR K usando un handle interno.
        La llave nunca se expone ni se devuelve fuera de la bóveda.
        """
        handle = self.get_handle(slot_name, "SGEN")
        return handle.use_for_signature(state)

    def get_audit_counters(self) -> Dict[str, int]:
        return dict(self._counters)

    def dump_vault(self, authorized: bool = False) -> Dict[str, Optional[int]]:
        """
        Estado de la bóveda para depuración.
        - authorized: True requiere permiso explícito.
        - Retorna { slot_name: int | None } sin exponer objetos internos.
        """
        if not authorized:
            self._counters["violations"] += 1
            raise VaultAccessError("Dump de bóveda requiere autorización")
        return {k: (int(v) if v is not None else None) for k, v in self._slots.items()}
