import sys
import os
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', 'isa')))

from register_file import RegisterFile
from isa_types import UInt64
from addressing_modes import (
    mode_REG, mode_REG_IMM, mode_BASE_DISP, mode_IMM_LONG,
    validate_address, describe_addressing
)


def test_mode_REG():
    rf = RegisterFile()
    rf.write('R1', UInt64(0x1000))
    result = mode_REG(rf, 'R1')
    print("test_mode_REG:", "PASSED" if result ==
          0x1000 else f"FAILED (got {result})")


def test_mode_REG_IMM():
    rf = RegisterFile()
    rf.write('R2', UInt64(0x2000))
    result = mode_REG_IMM(rf, 'R2', 0x30)
    expected = 0x2030
    print("test_mode_REG_IMM:", "PASSED" if result ==
          expected else f"FAILED (got {result})")


def test_mode_BASE_DISP():
    rf = RegisterFile()
    rf.write('R3', UInt64(0x3000))
    rf.write('R4', UInt64(0x40))
    result = mode_BASE_DISP(rf, 'R3', 'R4')
    expected = 0x3040
    print("test_mode_BASE_DISP:", "PASSED" if result ==
          expected else f"FAILED (got {result})")


def test_mode_IMM_LONG():
    result = mode_IMM_LONG(0x5000000000000000)
    expected = 0x5000000000000000
    print("test_mode_IMM_LONG:", "PASSED" if result ==
          expected else f"FAILED (got {result})")


def test_validate_address_safe():
    try:
        validate_address(0x1000, vault_range=(0x80000000, 0x800000FF))
        print("test_validate_address_safe: PASSED")
    except PermissionError:
        print("test_validate_address_safe: FAILED (unexpected rejection)")


def test_validate_address_blocked():
    try:
        validate_address(0x80000010, vault_range=(0x80000000, 0x800000FF))
        print("test_validate_address_blocked: FAILED (should have raised)")
    except PermissionError:
        print("test_validate_address_blocked: PASSED")


def test_describe_addressing():
    desc1 = describe_addressing('REG', rs1='R1')
    desc2 = describe_addressing('REG_IMM', rs1='R2', imm=0x20)
    desc3 = describe_addressing('BASE_DISP', base_reg='R3', disp_reg='R4')
    desc4 = describe_addressing('IMM_LONG', imm=0x12345678)
    print("test_describe_addressing:")
    print("  REG       →", desc1)
    print("  REG_IMM   →", desc2)
    print("  BASE_DISP →", desc3)
    print("  IMM_LONG  →", desc4)


# Ejecutar todas las pruebas
if __name__ == "__main__":
    test_mode_REG()
    test_mode_REG_IMM()
    test_mode_BASE_DISP()
    test_mode_IMM_LONG()
    test_validate_address_safe()
    test_validate_address_blocked()
    test_describe_addressing()
