# test2_isa_types.py
# Test para isa_types en cohesion con register_file

from isa.register_file import register_file
from isa.isa_types import UInt64, Vec4x64


def test_write_and_read():
    rf = register_file()
    rf.write('R1', UInt64(0x123456789ABCDEF0))
    result = rf.read('R1')
    expected = 0x123456789ABCDEF0
    print("test_write_and_read:", "PASSED" if result ==
          expected else f"FAILED (got {result})")


def test_masking():
    rf = register_file()
    rf.write('R2', UInt64(0x1FFFFFFFFFFFFFFFF))
    result = rf.read('R2')
    expected = 0xFFFFFFFFFFFFFFFF
    print("test_masking:", "PASSED" if result ==
          expected else f"FAILED (got {result})")


def test_vec4x64_xor():
    rf = register_file()
    state = Vec4x64(0xA, 0xB, 0xC, 0xD)
    key = UInt64(0xFF00FF00FF00FF00)
    signed = state.xor_with_key(key)
    passed = True
    for i in range(4):
        rf.write(f'R{i}', signed[i])
        if rf.read(f'R{i}') != signed[i]:
            passed = False
            print(f"test_vec4x64_xor: FAILED at R{i}")
    if passed:
        print("test_vec4x64_xor: PASSED")


def test_invalid_register():
    rf = register_file()
    try:
        rf.write('R32', 0x1)
        print("test_invalid_register: FAILED (no exception)")
    except ValueError:
        print("test_invalid_register: PASSED")


# Ejecutar todas las pruebas
if __name__ == "__main__":
    test_write_and_read()
    test_masking()
    test_vec4x64_xor()
    test_invalid_register()
