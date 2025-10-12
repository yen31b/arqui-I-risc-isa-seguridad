# test_register_file.py
# Pruebas manuales y descriptivas para register_file

import sys
import os
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', 'isa')))

from register_file import register_file

def run_tests():
    rf = register_file()

    print("\n=== TEST 1: Escritura y lectura de registro general ===")
    rf.write('R5', 0x123456789ABCDEF0)
    val = rf.read('R5')
    print(f"Se escribió 0x123456789ABCDEF0 en R5, se leyó: 0x{int(val):016x}")

    print("\n=== TEST 2: Escritura y lectura de registros especiales (PC, SR) ===")
    rf.write('PC', 0x1000)
    rf.write('SR', 0xDEAD)
    print(f"PC = 0x{int(rf.read('PC')):016x}, SR = 0x{int(rf.read('SR')):016x}")

    print("\n=== TEST 3: Aplicación de máscara a 64 bits ===")
    rf.write('R1', 0x1FFFFFFFFFFFFFFFF)  # valor de 65 bits
    val = rf.read('R1')
    print(f"Se escribió 0x1FFFFFFFFFFFFFFFF en R1, se leyó (enmascarado): 0x{int(val):016x}")

    print("\n=== TEST 4: Escritura en registro inválido ===")
    try:
        rf.write('R32', 0x1)
    except ValueError as e:
        print(f"Correcto: se bloqueó escritura en R32 → {e}")

    print("\n=== TEST 5: Lectura de registro inválido ===")
    try:
        rf.read('R32')
    except ValueError as e:
        print(f"Correcto: se bloqueó lectura en R32 → {e}")

    print("\n=== TEST 6: Dump de registros ===")
    rf.write('R0', 0xDEADBEEFDEADBEEF)
    rf.write('PC', 0xCAFEBABE)
    dump = rf.dump_registers()
    print("Dump parcial (solo no-cero):")
    for k, v in dump.items():
        if v != 0:
            print(f"  {k} = 0x{v:016x}")

    print("\n=== TEST 7: Escritura en registro reservado ===")
    try:
        rf.write('VAULT_KEY', 0x1234)
    except PermissionError as e:
        print(f"Correcto: se bloqueó escritura en registro reservado → {e}")

    print("\n=== TEST 8: Escritura de valor marcado como secreto de bóveda ===")
    class FakeVaultValue:
        _is_vault_secret = True
        def __int__(self): return 0x5555

    try:
        rf.write('R10', FakeVaultValue())
    except PermissionError as e:
        print(f"Correcto: se bloqueó escritura de valor secreto en R10 → {e}")

    print("\n=== TEST 9: Métricas de seguridad ===")
    metrics = rf.get_security_metrics()
    print("Métricas recolectadas:")
    for k, v in metrics.items():
        print(f"  {k}: {v}")

if __name__ == '__main__':
    run_tests()
