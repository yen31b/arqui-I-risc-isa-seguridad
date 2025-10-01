# test_pipeline.py

import sys
import os

# Agregar carpetas al path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'isa')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'pipeline')))

from isa_definition import encode_instruction
from pipeline import Pipeline

def test_pipeline():
    print("🔍 Iniciando test de Pipeline completo...")

    # Codificar instrucción: ADD R3 = R1 + R2
    instr = encode_instruction('R_TYPE', opcode=1, rd=3, rs1=1, rs2=2, funct=0)
    instructions = [instr]

    print(f"\n📦 Instrucción cargada en memoria: 0x{instr:08x}")

    # Inicializar pipeline
    pipe = Pipeline(instructions)

    # Pre-cargar valores en R1 y R2
    pipe.rf.write('R1', 15)
    pipe.rf.write('R2', 25)
    print("\n🧠 Estado inicial de registros:")
    print(f"→ R1: {pipe.rf.read('R1')}")
    print(f"→ R2: {pipe.rf.read('R2')}")
    print(f"→ PC: {pipe.rf.read('PC')}")

    # Ejecutar pipeline
    pipe.run()

    # Verificar resultado
    r3_val = pipe.rf.read('R3')
    print(f"\n✅ Verificando resultado final:")
    print(f"→ R3: {r3_val}")
    assert r3_val == 40, "❌ R3 debería contener 15 + 25 = 40"

    # Métricas
    metrics = pipe.get_metrics()
    print("\n📊 Métricas del pipeline:")
    print(f"→ Ciclos: {metrics['cycles']}")
    print(f"→ Fetch: {metrics['fetch']}")
    print(f"→ Decode: {metrics['decode']}")
    print(f"→ Execute: {metrics['execute']}")

    print("\n✅ Test de Pipeline exitoso.")

# Ejecutar el test
if __name__ == "__main__":
    test_pipeline()
