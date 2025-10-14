# test_execute_stage.py
import sys
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.append(ROOT)

from isa.isa_types import UInt64
from pipeline.execute_stage import ExecuteStage

def test_execute_stage():
    print("🔍 Iniciando test de ExecuteStage...")

    # Crear instancia de la etapa EX
    ex = ExecuteStage()

    # Simular instrucción decodificada: ADD R3 = R1 + R2
    decoded_instr = {
        'opcode_name': 'ADD',
        'operandos': {
            'rs1_val': 10,
            'rs2_val': 20,
            'rd': 3
        },
        'control_signals': {
            'is_arithmetic': True,
            'is_modular': False,
            'is_nonlin': False,
            'use_boveda': False,
            'needs_imm': False,
            'addressing_mode': 'REG'
        }
    }

    print("\n📤 Instrucción decodificada simulada:")
    print(f"→ Opcode: {decoded_instr['opcode_name']}")
    print(f"→ rs1_val: {decoded_instr['operandos']['rs1_val']}")
    print(f"→ rs2_val: {decoded_instr['operandos']['rs2_val']}")
    print(f"→ rd: {decoded_instr['operandos']['rd']}")
    print(f"→ Señales de control: {decoded_instr['control_signals']}")

    # Ejecutar la instrucción
    result = ex.execute(decoded_instr)

    print("\n⚙️ Resultado de ejecución:")
    print(f"→ Resultado: {result['result']}")
    print(f"→ Latencia: {result['latency']}")
    print(f"→ Señal de bóveda: {result['vault_signal']}")

    # Verificar resultado esperado
    assert result['result'] == UInt64(30), "❌ Resultado incorrecto para ADD"
    assert result['latency'] == 1, "❌ Latencia incorrecta para ADD"
    assert result['vault_signal'] is False, "❌ No debería haber señal de bóveda"

    # Métricas
    metrics = ex.get_metrics()
    print("\n📊 Métricas de ejecución:")
    print(f"→ Instrucciones ejecutadas: {metrics['exec_count']}")
    print(f"→ Ciclos acumulados: {metrics['cycles']}")
    print(f"→ Latencias por operación: {metrics['op_latency']}")

    print("\n✅ Test de ExecuteStage exitoso.")

# Ejecutar el test
if __name__ == "__main__":
    test_execute_stage()
