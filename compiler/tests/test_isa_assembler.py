import sys
import textwrap
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from isa import isa_definition as ISA

from compiler.isa_assembler import Assembler, AssemblyError, format_words


class IsaAssemblerTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.asm = Assembler()

    def test_basic_program_with_branch(self) -> None:
        source = textwrap.dedent(
            """
            start:
                ADDI R1, R0, 5
                ADDI R2, R0, 3
                ADD R3, R1, R2
                BEQ R3, R2, end
                JUMP start
            end:
                NOP
            """
        )
        words = self.asm.assemble(source)

        expected = [
            ISA.encode_instruction("I_TYPE", opcode=ISA.OPCODES['ADDI'], rd=1, rs1=0, imm=5),
            ISA.encode_instruction("I_TYPE", opcode=ISA.OPCODES['ADDI'], rd=2, rs1=0, imm=3),
            ISA.encode_instruction("R_TYPE", opcode=ISA.OPCODES['ADD'], rd=3, rs1=1, rs2=2, funct=0),
            ISA.encode_instruction("S_TYPE", opcode=ISA.OPCODES['BEQ'], rs1=3, rs2=2, imm=1),
            ISA.encode_instruction("I_TYPE", opcode=ISA.OPCODES['JUMP'], rd=0, rs1=0, imm=0),
            ISA.encode_instruction("R_TYPE", opcode=ISA.OPCODES['NOP'], rd=0, rs1=0, rs2=0, funct=0),
        ]
        self.assertEqual(words, expected)

    def test_memory_sequence(self) -> None:
        source = textwrap.dedent(
            """
                LOADI R4, 0x100
                LOADI R5, 0xABC
                STORE R4, R5, 0
                LOAD R6, R4, 0
            """
        )
        words = self.asm.assemble(source)
        expected = [
            ISA.encode_instruction("I_TYPE", opcode=ISA.OPCODES['LOADI'], rd=4, rs1=0, imm=0x100),
            ISA.encode_instruction("I_TYPE", opcode=ISA.OPCODES['LOADI'], rd=5, rs1=0, imm=0xABC),
            ISA.encode_instruction("S_TYPE", opcode=ISA.OPCODES['STORE'], rs1=4, rs2=5, imm=0),
            ISA.encode_instruction("I_TYPE", opcode=ISA.OPCODES['LOAD'], rd=6, rs1=4, imm=0),
        ]
        self.assertEqual(words, expected)

    def test_memory_parentheses_syntax(self) -> None:
        source = textwrap.dedent(
            """
                LOAD R1, 8(R2)
                STORE R3, -4(R4)
            """
        )
        words = self.asm.assemble(source)
        expected = [
            ISA.encode_instruction("I_TYPE", opcode=ISA.OPCODES['LOAD'], rd=1, rs1=2, imm=8),
            ISA.encode_instruction("S_TYPE", opcode=ISA.OPCODES['STORE'], rs1=4, rs2=3, imm=(1 << 16) - 4),
        ]
        self.assertEqual(words, expected)

    def test_vault_and_hash_defaults(self) -> None:
        source = textwrap.dedent(
            """
                VSTORE KEY_1, R2
                HASH_INIT R3
            """
        )
        words = self.asm.assemble(source)
        expected = [
            ISA.encode_instruction(
                "V_TYPE",
                opcode=ISA.OPCODES['VSTORE'],
                vault_idx=ISA.VAULT_SLOTS['KEY_1'],
                rs1=ISA.REGISTERS['R2'],
                funct=ISA.FUNCT_CODES['VAULT_KEY'],
            ),
            ISA.encode_instruction(
                "H_TYPE",
                opcode=ISA.OPCODES['HASH_INIT'],
                rs1=ISA.REGISTERS['R3'],
                funct=ISA.FUNCT_CODES['HASH_START'],
            ),
        ]
        self.assertEqual(words, expected)

    def test_toymdma_and_hash_mix_instructions(self) -> None:
        source = textwrap.dedent(
            """
                MIXMUL R1, R2, R3
                MODADD R4, R5, R6
                CALC_F R7, R8, R9
                CALC_G R10, R11, R12
                CALC_H R13, R14, R15
                NONLIN R16, R17
            """
        )
        words = self.asm.assemble(source)
        expected = [
            ISA.encode_instruction("R_TYPE", opcode=ISA.OPCODES['MIXMUL'], rd=1, rs1=2, rs2=3, funct=0),
            ISA.encode_instruction("R_TYPE", opcode=ISA.OPCODES['MODADD'], rd=4, rs1=5, rs2=6, funct=0),
            ISA.encode_instruction("R_TYPE", opcode=ISA.OPCODES['CALC_F'], rd=7, rs1=8, rs2=9, funct=0),
            ISA.encode_instruction("R_TYPE", opcode=ISA.OPCODES['CALC_G'], rd=10, rs1=11, rs2=12, funct=0),
            ISA.encode_instruction("R_TYPE", opcode=ISA.OPCODES['CALC_H'], rd=13, rs1=14, rs2=15, funct=0),
            ISA.encode_instruction("R_TYPE", opcode=ISA.OPCODES['NONLIN'], rd=16, rs1=17, rs2=0, funct=0),
        ]
        self.assertEqual(words, expected)

    def test_shift_instructions(self) -> None:
        source = textwrap.dedent(
            """
                SHIFTL R1, R2, R3
                SHIFTR R4, R5, R6
            """
        )
        words = self.asm.assemble(source)

        expected = [
            ISA.encode_instruction("R_TYPE", opcode=ISA.OPCODES['SHIFTL'], rd=1, rs1=2, rs2=3, funct=0),
            ISA.encode_instruction("R_TYPE", opcode=ISA.OPCODES['SHIFTR'], rd=4, rs1=5, rs2=6, funct=0),
        ]

        self.assertEqual(words, expected)

    def test_update_instruction_encoding(self) -> None:
        source = textwrap.dedent(
            """
                UPDATE_A R8, R8, R15, R17, R9
                UPDATE_D R20, R21, R22, R23, R24, 0x400
            """
        )
        words = self.asm.assemble(source)

        funct_a = ((ISA.REGISTERS['R17'] & 0x1F) << 5) | (ISA.REGISTERS['R9'] & 0x1F)
        funct_d = (((ISA.REGISTERS['R23'] & 0x1F) << 5) | (ISA.REGISTERS['R24'] & 0x1F) | 0x400) & 0x7FF

        expected = [
            ISA.encode_instruction(
                "R_TYPE",
                opcode=ISA.OPCODES['UPDATE_A'],
                rd=ISA.REGISTERS['R8'],
                rs1=ISA.REGISTERS['R8'],
                rs2=ISA.REGISTERS['R15'],
                funct=funct_a,
            ),
            ISA.encode_instruction(
                "R_TYPE",
                opcode=ISA.OPCODES['UPDATE_D'],
                rd=ISA.REGISTERS['R20'],
                rs1=ISA.REGISTERS['R21'],
                rs2=ISA.REGISTERS['R22'],
                funct=funct_d,
            ),
        ]

        self.assertEqual(words, expected)

    def test_extended_vault_ops(self) -> None:
        source = textwrap.dedent(
            """
                VLOAD HASH_A, R5
                KVW KEY_0, R1
                KVL KEY_2, R3
                KVOP KEY_3, R4, VAULT_KEY
                SGEN KEY_1, R7
            """
        )
        words = self.asm.assemble(source)

        expected = [
            ISA.encode_instruction(
                "V_TYPE",
                opcode=ISA.OPCODES['VLOAD'],
                vault_idx=ISA.VAULT_SLOTS['HASH_A'],
                rs1=ISA.REGISTERS['R5'],
                funct=0,
            ),
            ISA.encode_instruction(
                "V_TYPE",
                opcode=ISA.OPCODES['KVW'],
                vault_idx=ISA.VAULT_SLOTS['KEY_0'],
                rs1=ISA.REGISTERS['R1'],
                funct=0,
            ),
            ISA.encode_instruction(
                "V_TYPE",
                opcode=ISA.OPCODES['KVL'],
                vault_idx=ISA.VAULT_SLOTS['KEY_2'],
                rs1=ISA.REGISTERS['R3'],
                funct=0,
            ),
            ISA.encode_instruction(
                "V_TYPE",
                opcode=ISA.OPCODES['KVOP'],
                vault_idx=ISA.VAULT_SLOTS['KEY_3'],
                rs1=ISA.REGISTERS['R4'],
                funct=ISA.FUNCT_CODES['VAULT_KEY'],
            ),
            ISA.encode_instruction(
                "V_TYPE",
                opcode=ISA.OPCODES['SGEN'],
                vault_idx=ISA.VAULT_SLOTS['KEY_1'],
                rs1=ISA.REGISTERS['R7'],
                funct=0,
            ),
        ]

        self.assertEqual(words, expected)

    def test_word_directive_and_errors(self) -> None:
        words = self.asm.assemble(".word 0xDEADBEEF\n")
        self.assertEqual(words, [0xDEADBEEF])

        with self.assertRaises(AssemblyError):
            self.asm.assemble("UNKNOWN R1, R2, R3\n")


class FormatWordsTestCase(unittest.TestCase):
    def test_variants(self) -> None:
        words = [0x12345678]
        self.assertEqual(format_words(words, fmt="hex"), ["0x12345678"])
        self.assertEqual(format_words(words, fmt="bin"), ["00010010001101000101011001111000"])
        self.assertEqual(format_words(words, fmt="int"), [str(0x12345678)])
        with self.assertRaises(ValueError):
            format_words(words, fmt="oct")


if __name__ == "__main__":
    unittest.main()
