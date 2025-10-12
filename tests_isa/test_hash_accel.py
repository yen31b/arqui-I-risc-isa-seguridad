
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

    def test_update_a(self):
        # A = rol64(A + f + mul, 7) + B
        A = 0xAAAAAAAABBBBBBBB
        f = 0xCCCCCCCCDDDDDDDD
        mul = 0x1111111122222222
        B = 0x3333333344444444

        self.rf.write("R8", UInt64(A))   # A
        self.rf.write("R15", UInt64(f))  # f
        self.rf.write("R17", UInt64(mul))# mul
        self.rf.write("R9", UInt64(B))   # B

        # funct = (rs3 << 5) | rs4 → rs3 = R17, rs4 = R9
        funct = (17 << 5) | 9

        instr = {
            'opcode_name': 'UPDATE_A',
            'operandos': {
                'rs1_val': self.rf.read("R8"),   # A
                'rs2_val': self.rf.read("R15"),  # f
                'funct': funct
            },
            'control_signals': {}
        }

        temp = (A + f + mul) & MASK64
        rot = ((temp << 7) | (temp >> (64 - 7))) & MASK64
        expected = (rot + B) & MASK64

        result = self.exec_stage.execute(instr)['result']
        self.assertEqual(int(result), expected)

    def test_update_b(self):
        # B = rol64(B + g + block, 11) + (C * 3)
        B = 0xCCCCCCCCDDDDDDDD
        g = 0xEEEEEEEEFFFFFFFF
        block = 0xCAFEBABEDEADBEEF
        C = 0x123456789ABCDEF0

        self.rf.write("R9", UInt64(B))       # B
        self.rf.write("R14", UInt64(g))      # g
        self.rf.write("R3", UInt64(block))   # block
        self.rf.write("R10", UInt64(C))      # C

        funct = (3 << 5) | 10  # rs3 = R3, rs4 = R10

        instr = {
            'opcode_name': 'UPDATE_B',
            'operandos': {
                'rs1_val': self.rf.read("R9"),   # B
                'rs2_val': self.rf.read("R14"),  # g
                'funct': funct
            },
            'control_signals': {}
        }

        temp = (B + g + block) & MASK64
        rot = ((temp << 11) | (temp >> (64 - 11))) & MASK64
        expected = (rot + (C * 3)) & MASK64

        result = self.exec_stage.execute(instr)['result']
        self.assertEqual(int(result), expected)

    def test_update_c(self):
        # C = rol64(C + h + mul, 17) + (D % PRIME_MOD)
        C = 0xEEEEEEEEFFFFFFFF
        h = 0xAAAAAAAABBBBBBBB
        mul = 0xCAFEBABEDEADBEEF
        D = 0x123456789ABCDEF0
        prime = TOYMDMA_CONSTANTS['PRIME_MOD']

        self.rf.write("R10", UInt64(C))      # C
        self.rf.write("R16", UInt64(h))      # h
        self.rf.write("R17", UInt64(mul))    # mul
        self.rf.write("R11", UInt64(D))      # D

        funct = (17 << 5) | 11  # rs3 = R17, rs4 = R11

        instr = {
            'opcode_name': 'UPDATE_C',
            'operandos': {
                'rs1_val': self.rf.read("R10"),  # C
                'rs2_val': self.rf.read("R16"),  # h
                'funct': funct
            },
            'control_signals': {}
        }

        temp = (C + h + mul) & MASK64
        rot = ((temp << 17) | (temp >> (64 - 17))) & MASK64
        expected = (rot + (D % prime)) & MASK64

        result = self.exec_stage.execute(instr)['result']
        self.assertEqual(int(result), expected)

    def test_update_d(self):
        # D = rol64(D + A + block, 19) ^ (f * 5)
        D = 0x123456789ABCDEF0
        A = 0xAAAAAAAABBBBBBBB
        block = 0xCAFEBABEDEADBEEF
        f = 0xCCCCCCCCDDDDDDDD

        self.rf.write("R11", UInt64(D))      # D
        self.rf.write("R8", UInt64(A))       # A
        self.rf.write("R3", UInt64(block))   # block
        self.rf.write("R15", UInt64(f))      # f

        funct = (3 << 5) | 15  # rs3 = R3, rs4 = R15

        instr = {
            'opcode_name': 'UPDATE_D',
            'operandos': {
                'rs1_val': self.rf.read("R11"),  # D
                'rs2_val': self.rf.read("R8"),   # A
                'funct': funct
            },
            'control_signals': {}
        }

        temp = (D + A + block) & MASK64
        rot = ((temp << 19) | (temp >> (64 - 19))) & MASK64
        expected = (rot ^ (f * 5)) & MASK64

        result = self.exec_stage.execute(instr)['result']
        self.assertEqual(int(result), expected)





if __name__ == '__main__':
    unittest.main()
   