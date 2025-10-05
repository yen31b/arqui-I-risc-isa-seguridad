import textwrap
import unittest

import isa_definition as ISA

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
