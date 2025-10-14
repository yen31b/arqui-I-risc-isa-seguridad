import sys, os
from pathlib import Path

# Asegurar que la raíz del proyecto esté en sys.path para poder importar isa/ y pipeline/
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Importar usando paquetes raíz
from isa.isa_definition import encode_instruction, OPCODES
from pipeline.pipeline import Pipeline

def main():
    print("=== Test Pipeline Simple: ADDI x2 then ADD ===")

    # Instrucciones: R1 = 10; R2 = 20; R3 = R1 + R2
    instr1 = encode_instruction('I_TYPE', opcode=OPCODES['ADDI'], rd=1, rs1=0, imm=10)
    instr2 = encode_instruction('I_TYPE', opcode=OPCODES['ADDI'], rd=2, rs1=0, imm=20)
    instr3 = encode_instruction('R_TYPE', opcode=OPCODES['ADD'], rd=3, rs1=1, rs2=2, funct=0)

    program = [instr1, instr2, instr3]

    print(f"Loaded instructions (count={len(program)}):")
    for i, ins in enumerate(program):
        print(f"  [{i}] 0x{ins:08x}")

    # Inicializar pipeline y ejecutar todo
    p = Pipeline(program)
    p.run()

    # Comprobaciones
    r1 = int(p.rf.read('R1'))
    r2 = int(p.rf.read('R2'))
    r3 = int(p.rf.read('R3'))
    expected = 10 + 20

    print("\n--- Results ---")
    print(f"R1 expected: 10, got: {r1}")
    print(f"R2 expected: 20, got: {r2}")
    print(f"R3 expected: {expected}, got: {r3}")

    assert r1 == 10, f"R1 mismatch: {r1}"
    assert r2 == 20, f"R2 mismatch: {r2}"
    assert r3 == expected, f"R3 mismatch: expected {expected}, got {r3}"

    # Mostrar métricas resumidas
    metrics = p.get_metrics()
    print("\n--- Pipeline metrics ---")
    print(f"Instructions completed: {metrics.get('instructions_completed', len(p.completed))}")
    print(f"Estimated total cycles (sum EX+MEM latencies): {metrics.get('total_cycles_estimated', p.get_cycle)}")
    mem = metrics.get('memory', {})
    if mem:
        print("Memory metrics:", mem)

    print("\nTest passed.")

if __name__ == "__main__":
    main()