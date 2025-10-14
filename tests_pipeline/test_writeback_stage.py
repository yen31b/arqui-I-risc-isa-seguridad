# test_writeback_stage.py
# Pruebas manuales y descriptivas para WriteBackStage

import sys
import os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.append(ROOT)

from isa.isa_types import UInt64, Vec4x64
from isa.register_file import register_file
from pipeline.writeback_stage import WriteBackStage

def run_tests():
    rf = register_file()
    wb = WriteBackStage(rf)

    print("\n=== TEST 1: Escritura normal en registro ===")
    decoded = {'operandos': {'rd': 5}, 'opcode_name': 'ADD'}
    mem_result = {'result': UInt64(0x1234)}
    wb.execute(mem_result, decoded)
    print(f"R5 después de WB = 0x{int(rf.read('R5')):016x}")

    print("\n=== TEST 2: Escritura de resultado especial (Vec4x64) ===")
    decoded = {'operandos': {'rd': 8}, 'opcode_name': 'HASH_FINAL'}
    vec = Vec4x64([UInt64(1), UInt64(2), UInt64(3), UInt64(4)])
    mem_result = {'result': vec}
    wb.execute(mem_result, decoded)
    print(f"R8 después de WB (vector) = {rf.read('R8')}")

    print("\n=== TEST 3: Bloqueo de escritura de valor secreto de bóveda ===")
    class FakeVaultSecret(UInt64):
        _is_vault_secret = True

    decoded = {'operandos': {'rd': 10}, 'opcode_name': 'KVL'}
    mem_result = {'result': FakeVaultSecret(0x9999)}

    prev_val = rf.read('R10')
    wb.execute(mem_result, decoded)
    after_val = rf.read('R10')

    print(f"R10 antes = 0x{int(prev_val):016x}, después = 0x{int(after_val):016x}")
    if int(prev_val) == int(after_val):
        print("✅ Correcto: el valor secreto NO sobrescribió el registro")
    else:
        print("❌ Error: el valor secreto modificó el registro")

    print("\n=== TEST 4: Métricas de WB ===")
    metrics = wb.get_metrics()
    for k, v in metrics.items():
        print(f"  {k}: {v}")

if __name__ == '__main__':
    run_tests()
