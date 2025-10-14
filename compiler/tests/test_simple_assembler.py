import textwrap
import unittest
import os
import sys

# Asegurar que la raíz del proyecto esté en sys.path para importar 'compiler'
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from compiler.simple_assembler import Assembler, AssemblyError
from compiler.simple_assembler.cli import format_words


class SimpleAssemblerTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.asm = Assembler()

    def test_r_type_encoding(self) -> None:
        words = self.asm.assemble("ADD R1, R2, R3\n")
        self.assertEqual(words, [0x12980000])

    def test_i_type_encoding(self) -> None:
        words = self.asm.assemble("ADDI R1, R0, 5\n")
        self.assertEqual(words, [0x62000005])

    def test_branch_and_label(self) -> None:
        program = textwrap.dedent(
            """
            LOOP: ADDI R1, R1, -1
                  BEQ R1, R0, END
                  JMP LOOP
            END:  HALT R0, R0, R0
            """
        )
        words = self.asm.assemble(program)
        self.assertEqual(words, [0x6247FFFF, 0x80400001, 0x70000000, 0xF0000000])

    def test_word_directive(self) -> None:
        words = self.asm.assemble(".word 0xDEADBEEF\n")
        self.assertEqual(words, [0xDEADBEEF])

    def test_invalid_register(self) -> None:
        with self.assertRaises(AssemblyError):
            self.asm.assemble("ADD R8, R1, R2\n")


class FormatWordsTestCase(unittest.TestCase):
    def test_format_variants(self) -> None:
        words = [0x12345678]
        self.assertEqual(format_words(words, fmt="bin"), ["00010010001101000101011001111000"])
        self.assertEqual(format_words(words, fmt="hex"), ["0x12345678"])
        self.assertEqual(format_words(words, fmt="int"), [str(0x12345678)])
        with self.assertRaises(ValueError):
            format_words(words, fmt="oct")


if __name__ == "__main__":
    unittest.main()
