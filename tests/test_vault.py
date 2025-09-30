import unittest
from isa.vault import KeyVault, VaultAccessError
from drafts.isa_definition import VAULT_SLOTS
from isa.isa_types import UInt64

class TestKeyVault(unittest.TestCase):
    def setUp(self):
        self.kv = KeyVault()
        # elegir un slot válido para pruebas
        self.slot_key = 'KEY_0'
        self.slot_hash = 'HASH_A'

    def test_unauthorized_write_raises(self):
        with self.assertRaises(VaultAccessError):
            self.kv.write_slot(self.slot_key, 0x1234, authorized=False)

    def test_authorized_write_and_atomic_access(self):
        self.kv.write_slot(self.slot_key, 0xDEADBEEFCAFEBABE, authorized=True)
        val = self.kv.access_slot_for_operation(self.slot_key, 'KVL')
        self.assertEqual(int(val), 0xDEADBEEFCAFEBABE)

    def test_access_with_wrong_operation_raises(self):
        self.kv.write_slot(self.slot_hash, 0x1, authorized=True)
        with self.assertRaises(VaultAccessError):
            self.kv.access_slot_for_operation(self.slot_hash, 'READ')  # operación no permitida

    def test_dump_requires_authorization_and_returns_slots(self):
        self.kv.write_slot(self.slot_key, 0xAA55AA55AA55AA55, authorized=True)
        with self.assertRaises(VaultAccessError):
            self.kv.dump_vault(authorized=False)
        dumped = self.kv.dump_vault(authorized=True)
        self.assertIn(self.slot_key, dumped)
        self.assertEqual(int(dumped[self.slot_key]), 0xAA55AA55AA55AA55)

    def test_audit_counters_increment(self):
        before = self.kv.get_audit_counters()
        self.assertEqual(before['reads'], 0)
        self.kv.write_slot(self.slot_key, 0x10, authorized=True)
        _ = self.kv.access_slot_for_operation(self.slot_key, 'KVL')
        after = self.kv.get_audit_counters()
        self.assertEqual(after['writes'], 1)
        self.assertEqual(after['reads'], 1)
        self.assertEqual(after['ops'], 1)

if __name__ == '__main__':
    unittest.main()
