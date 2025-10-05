
import sys
import os
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', 'isa')))

from simulator_core import execute_instruction, MEMORY
from isa_definition import encode_instruction, OPCODES
from register_file import register_file
from isa_types import UInt64


def test_addi():
    rf = register_file()
    rf.write('R2', UInt64(0x100))
    instr = encode_instruction(
        'I_TYPE', opcode=OPCODES['ADDI'], rd=1, rs1=2, imm=0x20)
    execute_instruction(instr, rf)
    result = rf.read('R1')
    expected = 0x120
    print("test_addi:", "PASSED" if result ==
          expected else f"FAILED (got {result})")


def test_load():
    rf = register_file()
    rf.write('R3', UInt64(0x200))
    MEMORY[0x220] = UInt64(0xDEADBEEFCAFEBABE)
    instr = encode_instruction(
        'I_TYPE', opcode=OPCODES['LOAD'], rd=4, rs1=3, imm=0x20)
    execute_instruction(instr, rf)
    result = rf.read('R4')
    expected = 0xDEADBEEFCAFEBABE
    print("test_load:", "PASSED" if result ==
          expected else f"FAILED (got {result})")


def test_store():
    rf = register_file()
    rf.write('R5', UInt64(0x300))
    rf.write('R6', UInt64(0x40))
    rf.write('R5', UInt64(0xBEEF1234567890AB))  # Valor a almacenar
    instr = encode_instruction(
        'S_TYPE', opcode=OPCODES['STORE'], rs1=5, rs2=6, imm=0x0)
    execute_instruction(instr, rf)
    addr = rf.read('R5') + rf.read('R6')
    result = MEMORY.get(addr)
    expected = 0xBEEF1234567890AB
    print("test_store:", "PASSED" if result ==
          expected else f"FAILED (got {result})")


# Ejecutar todas las pruebas
if __name__ == "__main__":
    test_addi()
    test_load()
    test_store()
