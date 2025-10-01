# test_decode_stage.py

import sys
import os
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', 'pipeline')))

from decode_stage import DecodeStage
from register_file import register_file
from isa_definition import encode_instruction


def test_decode_stage():
    print("🔍 Iniciando test de DecodeStage...")

    # Crear banco de registros simulado
    rf = register_file()
    rf.write('R1', 10)
    rf.write('R2', 20)

    # Crear instancia del decodificador
    decoder = DecodeStage(rf)

    # Codificar una instrucción tipo R: ADD R3 = R1 + R2
    instr = encode_instruction('R_TYPE', opcode=1, rd=3, rs1=1, rs2=2, funct=0)

    print(f"📦 Instrucción codificada: 0x{instr:08x}")

    # Decodificar la instrucción
    result = decoder.decode(instr)

    print("\n📤 Resultado de decodificación:")
    print(f"→ Opcode name: {result['opcode_name']}")
    print(f"→ Formato: {result['format_type']}")
    print(f"→ Operandos extraídos:")
    for field, value in result['operandos'].items():
        print(f"   - {field}: {value}")

    print("\n🎛️ Señales de control generadas:")
    for signal, value in result['control_signals'].items():
        print(f"   - {signal}: {value}")

    # Verificar valores esperados
    assert result['opcode_name'] == 'ADD', "❌ Opcode incorrecto"
    assert result['format_type'] == 'R_TYPE', "❌ Formato incorrecto"
    assert result['operandos']['rd'] == 3, "❌ rd incorrecto"
    assert result['operandos']['rs1'] == 1, "❌ rs1 incorrecto"
    assert result['operandos']['rs2'] == 2, "❌ rs2 incorrecto"
    assert result['control_signals']['is_arithmetic'] is True, "❌ Señal is_arithmetic incorrecta"

    # Métricas
    metrics = decoder.get_metrics()
    print("\n📊 Métricas de decodificación:")
    print(f"→ Instrucciones decodificadas: {metrics['decode_count']}")
    print(f"→ Ciclos acumulados: {metrics['cycles']}")

    print("\n✅ Test de DecodeStage exitoso.")


# Ejecutar el test
if __name__ == "__main__":
    test_decode_stage()
