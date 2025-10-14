# test_fetch_stage.py

import sys
import os
# Asegurar raíz del proyecto en sys.path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from pipeline.fetch_stage import InstructionMemory, FetchStage
from isa.register_file import register_file

def test_fetch_stage():
    print("🔍 Iniciando test de FetchStage...")

    # Simular instrucciones como enteros de 32 bits
    instructions = [
        0x00000001,  # NOP
        0x00000002,  # ADD
        0x00000003   # SUB
    ]

    print("📦 Memoria de instrucciones inicializada con 3 instrucciones:")
    for i, instr in enumerate(instructions):
        print(f"   - Dirección {i*4:02x}: 0x{instr:08x}")

    # Inicializar memoria de instrucciones y banco de registros
    instr_mem = InstructionMemory(instructions)
    rf = register_file()
    rf.write('PC', 0)  # Comenzar en dirección 0

    print("\n🧠 Estado inicial del PC:", rf.read('PC'))

    # Crear etapa de fetch
    fetch = FetchStage(rf, instr_mem)

    # Ejecutar tres ciclos de fetch
    print("\n🚀 Ejecutando ciclos de fetch...")
    instr1 = fetch.step()
    print(
        f"→ Ciclo 1: instrucción = 0x{instr1:08x}, nuevo PC = {rf.read('PC')}")

    instr2 = fetch.step()
    print(
        f"→ Ciclo 2: instrucción = 0x{instr2:08x}, nuevo PC = {rf.read('PC')}")

    instr3 = fetch.step()
    print(
        f"→ Ciclo 3: instrucción = 0x{instr3:08x}, nuevo PC = {rf.read('PC')}")

    # Verificar resultados
    print("\n✅ Verificando resultados...")
    assert instr1 == 0x00000001, "❌ Primera instrucción incorrecta"
    assert instr2 == 0x00000002, "❌ Segunda instrucción incorrecta"
    assert instr3 == 0x00000003, "❌ Tercera instrucción incorrecta"
    assert rf.read('PC') == 12, "❌ PC no se incrementó correctamente"

    # Verificar métricas
    metrics = fetch.get_metrics()
    print("\n📊 Métricas de FetchStage:")
    print(f"→ Instrucciones fetchadas: {metrics['fetch_count']}")
    print(f"→ Ciclos acumulados: {metrics['cycles']}")

    print("\n✅ Test de FetchStage exitoso.")


# Ejecutar el test
if __name__ == "__main__":
    test_fetch_stage()
