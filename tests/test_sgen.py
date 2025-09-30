import unittest
from isa.vault import KeyVault, VaultAccessError
from isa.isa_types import Vec4x64, UInt64

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

if __name__ == '__main__':
    unittest.main()
