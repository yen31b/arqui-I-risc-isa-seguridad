# test_register_file.py
# Test para register_file

import unittest
from register_file import register_file


class test_register_file(unittest.TestCase):

    def setUp(self):
        self.rf = register_file()

    def test_write_and_read_general_register(self):
        self.rf.write('R5', 0x123456789ABCDEF0)
        value = self.rf.read('R5')
        self.assertEqual(value, 0x123456789ABCDEF0)

    def test_write_and_read_special_registers(self):
        self.rf.write('PC', 0x1000)
        self.rf.write('SR', 0xDEAD)
        self.assertEqual(self.rf.read('PC'), 0x1000)
        self.assertEqual(self.rf.read('SR'), 0xDEAD)

    def test_masking_to_64_bits(self):
        self.rf.write('R1', 0x1FFFFFFFFFFFFFFFF)
        value = self.rf.read('R1')
        self.assertEqual(value, 0xFFFFFFFFFFFFFFFF)

    def test_invalid_register_write(self):
        with self.assertRaises(ValueError):
            self.rf.write('R32', 0x1)

    def test_invalid_register_read(self):
        with self.assertRaises(ValueError):
            self.rf.read('R32')

    def test_dump_registers_output(self):
        # Just ensure it runs without error; visual inspection can be done manually
        self.rf.write('R0', 0xDEADBEEFDEADBEEF)
        self.rf.write('PC', 0xCAFEBABE)
        self.rf.dump_registers()


if __name__ == '__main__':
    unittest.main()
