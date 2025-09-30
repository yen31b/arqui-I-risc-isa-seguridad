# test2_isa_types.py
# Test para isa_types en cohesion con register_file

import unittest
from register_file import register_file
from isa_types import UInt64, Vec4x64
from vault import KeyVault, VaultAccessError


class TestRegisterFile(unittest.TestCase):
    def test_write_and_read(self):
        rf = register_file()
        rf.write('R1', UInt64(0x123456789ABCDEF0))
        result = rf.read('R1')
        self.assertEqual(int(result), 0x123456789ABCDEF0)

    def test_masking(self):
        rf = register_file()
        rf.write('R2', UInt64(0x1FFFFFFFFFFFFFFFF))
        result = rf.read('R2')
        self.assertEqual(int(result), 0xFFFFFFFFFFFFFFFF)

    def test_vec4x64_xor(self):
        rf = register_file()
        state = Vec4x64(0xA, 0xB, 0xC, 0xD)
        key = UInt64(0xFF00FF00FF00FF00)
        signed = state.xor_with_key(key)
        for i in range(4):
            rf.write(f'R{i}', signed[i])
            self.assertEqual(int(rf.read(f'R{i}')), int(signed[i]))

    def test_invalid_register(self):
        rf = register_file()
        with self.assertRaises(ValueError):
            rf.write('R32', 0x1)


class TestSGEN(unittest.TestCase):
    def setUp(self):
        self.kv = KeyVault()
        self.slot = 'KEY_0'
        self.state = Vec4x64(0x1, 0x2, 0x3, 0x4)
        self.key = UInt64(0xFF00FF00FF00FF00)

    def test_generate_signature_success(self):
        # Inicializar llave (autorizada)
        self.kv.write_slot(self.slot, int(self.key), authorized=True)
        sig = self.kv.generate_signature(self.slot, self.state)
        expected = self.state.xor_with_key(self.key)
        for i in range(4):
            self.assertEqual(int(sig[i]), int(expected[i]))

    def test_generate_signature_requires_key_initialized(self):
        # Si no se inicializa la llave, debe fallar al intentar generar la firma
        with self.assertRaises(VaultAccessError):
            _ = self.kv.generate_signature(self.slot, self.state)


# Ejecutar todas las pruebas
if __name__ == "__main__":
    unittest.main()
