
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

#  Nuevas pruebas para instrucciones CALC_F, CALC_G, CALC_H
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', 'pipeline')))
from execute_stage import ExecuteStage
from register_file import register_file

class TestCalcInstructions(unittest.TestCase):
    def setUp(self):
        self.rf = register_file()
        self.exec_stage = ExecuteStage()
        self.exec_stage.rf = self.rf  # Inyectar el banco de registros

        # Inicializar registros fuente
        self.rf.write("R8", UInt64(0xAAAAAAAABBBBBBBB))   # A
        self.rf.write("R9", UInt64(0xCCCCCCCCDDDDDDDD))   # B
        self.rf.write("R10", UInt64(0xEEEEEEEEFFFFFFFF))  # C
        self.rf.write("R11", UInt64(0x123456789ABCDEF0))  # D

    def test_calc_f(self):
        instr = {
            'opcode_name': 'CALC_F',
            'operandos': {
                'rs1_val': self.rf.read("R8"),  # A
                'rs2_val': self.rf.read("R9"),  # B
            },
            'control_signals': {}
        }
        A = 0xAAAAAAAABBBBBBBB
        B = 0xCCCCCCCCDDDDDDDD
        C = 0xEEEEEEEEFFFFFFFF
        expected = (A & B) ^ (A & C)
        result = self.exec_stage.execute(instr)['result']
        self.assertEqual(result, expected)

    def test_calc_g(self):
        instr = {
            'opcode_name': 'CALC_G',
            'operandos': {
                'rs1_val': self.rf.read("R9"),   # B
                'rs2_val': self.rf.read("R10"),  # C
            },
            'control_signals': {}
        }
        B = 0xCCCCCCCCDDDDDDDD
        C = 0xEEEEEEEEFFFFFFFF
        D = 0x123456789ABCDEF0
        expected = (B & C) ^ (~B & D)
        result = self.exec_stage.execute(instr)['result']
        self.assertEqual(result & MASK64, expected & MASK64)

    def test_calc_h(self):
        instr = {
            'opcode_name': 'CALC_H',
            'operandos': {
                'rs1_val': self.rf.read("R8"),  # A
                'rs2_val': self.rf.read("R9"),  # B
            },
            'control_signals': {}
        }
        A = 0xAAAAAAAABBBBBBBB
        B = 0xCCCCCCCCDDDDDDDD
        C = 0xEEEEEEEEFFFFFFFF
        D = 0x123456789ABCDEF0
        expected = A ^ B ^ C ^ D
        result = self.exec_stage.execute(instr)['result']
        self.assertEqual(result, expected)



if __name__ == '__main__':
    unittest.main()
