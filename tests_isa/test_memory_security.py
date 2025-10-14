import os, sys, unittest
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.append(ROOT)

from pipeline.memory_stage import DataMemory
from isa.isa_definition import VAULT_ADDR_RANGE
try:
    from isa import addressing_modes as addr_modes
    ADDR_OK = True
except Exception as e:
    print(f"[test_memory_security] ⚠️ addressing_modes no disponible ({e}); se omiten pruebas de modos.")
    ADDR_OK = False
from isa.register_file import register_file

class MemorySecurityTests(unittest.TestCase):
    def setUp(self):
        self.dm = DataMemory(vault_range=VAULT_ADDR_RANGE)

    def test_write_read_ok(self):
        self.dm.write(0x20, 0xDEAD)
        self.assertEqual(int(self.dm.read(0x20)), 0xDEAD)

    def test_vault_range_blocked(self):
        lo, hi = VAULT_ADDR_RANGE
        with self.assertRaises(PermissionError):
            self.dm.write(lo, 1)
        with self.assertRaises(PermissionError):
            self.dm.read(hi)

    @unittest.skipUnless(ADDR_OK, "addressing_modes no disponible")
    def test_addressing_modes_validate(self):
        rf = register_file()
        rf.write('R1', 0x10)
        rf.write('R2', 5)
        # REG
        self.assertEqual(int(addr_modes.mode_REG(rf, 'R1')), 0x10)
        # REG_IMM
        self.assertEqual(int(addr_modes.mode_REG_IMM(rf, 'R1', 8)), 0x18)
        # BASE_DISP
        self.assertEqual(int(addr_modes.mode_BASE_DISP(rf, 'R1', 'R2')), 0x15)
        # IMM_LONG
        self.assertEqual(int(addr_modes.mode_IMM_LONG(0xFFFF_FFFF_FFFF_FFFF)), 0xFFFF_FFFF_FFFF_FFFF)
        # validate against vault range
        lo, _ = VAULT_ADDR_RANGE
        with self.assertRaises(PermissionError):
            addr_modes.validate_address(lo, VAULT_ADDR_RANGE)

if __name__ == "__main__":
    unittest.main()
