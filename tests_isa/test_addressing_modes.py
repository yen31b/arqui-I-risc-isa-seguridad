import sys
import os
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', 'isa')))

from register_file import register_file
from isa_types import UInt64
from addressing_modes import (
    mode_REG, mode_REG_IMM, mode_BASE_DISP, mode_IMM_LONG,
    validate_address, describe_addressing, get_security_metrics
)
from isa_definition import VAULT_ADDR_RANGE


def test_mode_REG():
    rf = register_file()
    rf.write('R1', UInt64(0x5000))
    result = mode_REG(rf, 'R1')
    print("test_mode_REG:", "PASSED" if result == 0x5000 else f"FAILED (got {result})")


def test_mode_REG_IMM():
    rf = register_file()
    rf.write('R2', UInt64(0x2000))
    result = mode_REG_IMM(rf, 'R2', 0x30)
    expected = 0x2030
    print("test_mode_REG_IMM:", "PASSED" if result == expected else f"FAILED (got {result})")


def test_mode_BASE_DISP():
    rf = register_file()
    rf.write('R3', UInt64(0x3000))
    rf.write('R4', UInt64(0x40))
    result = mode_BASE_DISP(rf, 'R3', 'R4')
    expected = 0x3040
    print("test_mode_BASE_DISP:", "PASSED" if result == expected else f"FAILED (got {result})")


def test_mode_IMM_LONG():
    result = mode_IMM_LONG(0x5000000000000000)
    expected = 0x5000000000000000
    print("test_mode_IMM_LONG:", "PASSED" if result == expected else f"FAILED (got {result})")


def test_validate_address_safe():
    try:
        validate_address(0x50000000, vault_range=VAULT_ADDR_RANGE)
        print("test_validate_address_safe: PASSED")
    except PermissionError:
        print("test_validate_address_safe: FAILED (unexpected rejection)")


def test_validate_address_blocked():
    try:
        # Tomamos una dirección dentro del rango de bóveda
        start, end = VAULT_ADDR_RANGE
        blocked_addr = start + 1
        validate_address(blocked_addr, vault_range=VAULT_ADDR_RANGE)
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


def test_vault_violation_metrics():
    start, end = VAULT_ADDR_RANGE
    rf = register_file()
    rf.write('R5', UInt64(start))  # dirección dentro de la bóveda
    try:
        mode_REG(rf, 'R5')
    except PermissionError:
        print("test_vault_violation_metrics: acceso bloqueado correctamente")

    metrics = get_security_metrics()
    print("Métricas de seguridad:", metrics)


# Ejecutar todas las pruebas
if __name__ == "__main__":
    test_mode_REG()
    test_mode_REG_IMM()
    test_mode_BASE_DISP()
    test_mode_IMM_LONG()
    test_validate_address_safe()
    test_validate_address_blocked()
    test_describe_addressing()
    test_vault_violation_metrics()
