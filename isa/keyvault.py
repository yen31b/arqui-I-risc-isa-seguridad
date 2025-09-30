"""
keyvault.py

Compatibilidad histórica: reexporta KeyVault desde isa.vault para mantener
compatibilidad con módulos/scrips que importaban 'keyvault'.
No contiene implementación propia, sólo alias.
"""

from isa.vault import *
# Tipos mínimos
UInt64 = int

class Vec4x64:
    def __init__(self, a, b, c, d):
        self.values = [a & 0xFFFFFFFFFFFFFFFF,
                       b & 0xFFFFFFFFFFFFFFFF,
                       c & 0xFFFFFFFFFFFFFFFF,
                       d & 0xFFFFFFFFFFFFFFFF]

    def xor_with_key(self, k: int):
        k = k & 0xFFFFFFFFFFFFFFFF
        return Vec4x64(*(v ^ k for v in self.values))

    def __repr__(self):
        return f"Vec4x64({', '.join(hex(v) for v in self.values)})"

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
        if slot_name not in self._slots:
            raise VaultAccessError(f"Slot inválido: {slot_name}")
        if not authorized:
            raise VaultAccessError("Escritura en bóveda prohibida")
        self._slots[slot_name] = self._mask64(value)
        self._counters['writes'] += 1
        print(f"[KV] Escrito {hex(value)} en {slot_name}")

    def access_slot_for_operation(self, slot_name: str, operation: str):
        if slot_name not in self._slots:
            raise VaultAccessError(f"Slot inválido: {slot_name}")
        if self._slots[slot_name] is None:
            raise VaultAccessError(f"Slot {slot_name} no inicializado")

        allowed_ops = {'KVL', 'KVOP', 'SGEN'}
        if operation not in allowed_ops:
            raise VaultAccessError(f"Operación '{operation}' no permitida")

        self._counters['reads'] += 1
        self._counters['ops'] += 1
        print(f"[KV] Acceso controlado a {slot_name} para {operation}")
        return self._slots[slot_name]

    def generate_signature(self, slot_name: str, state: Vec4x64):
        key = self.access_slot_for_operation(slot_name, 'SGEN')
        sig = state.xor_with_key(key)
        print(f"[KV] Firma generada con {slot_name} → {sig}")
        return sig

    def get_audit_counters(self):
        return dict(self._counters)

    def dump_vault(self, authorized: bool = False):
        if not authorized:
            raise VaultAccessError("Dump requiere autorización")
        return dict(self._slots)

