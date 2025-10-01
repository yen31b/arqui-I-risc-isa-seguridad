
import sys
import os
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', 'isa')))

import unittest
from hash_accel import mixmul, modadd, nonlin, apply_block
from isa_definition import TOYMDMA_CONSTANTS
from isa_types import Vec4x64, UInt64

MASK64 = 0xFFFFFFFFFFFFFFFF

class TestHashAccel(unittest.TestCase):
    def test_mixmul_basic(self):
        a = 0x2
        b = 0x3
        gr = TOYMDMA_CONSTANTS['GOLDEN_RATIO']
        expected = ((a ^ gr) * b) & MASK64
        res = mixmul(a, b)
        self.assertEqual(int(res), expected)

    def test_modadd_default_mod(self):
        a = 5
        b = 7
        mod = TOYMDMA_CONSTANTS['PRIME_MOD']
        expected = (a + b) % mod
        res = modadd(a, b)
        self.assertEqual(int(res), expected)

    def test_nonlin_returns_uint64(self):
        x = 0x123456789ABCDEF0
        r = nonlin(x)
        self.assertIsInstance(r, UInt64)
        # determinismo: llamar dos veces devuelve mismo valor
        self.assertEqual(int(r), int(nonlin(x)))

    def test_apply_block_updates_state(self):
        st = Vec4x64(0x1, 0x2, 0x3, 0x4)
        new_st = apply_block(st, 0xCAFEBABEDEADBEEF)
        self.assertIsInstance(new_st, Vec4x64)
        # componentes deben ser UInt64 y distintos (en la mayoría de casos) del estado original
        for i in range(4):
            self.assertIsInstance(new_st[i], UInt64)
        # Al menos una componente debe cambiar respecto al estado inicial
        changed = any(int(new_st[i]) != int(st[i]) for i in range(4))
        self.assertTrue(changed)

if __name__ == '__main__':
    unittest.main()
