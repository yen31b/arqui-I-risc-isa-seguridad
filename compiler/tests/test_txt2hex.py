# test_txt2hex.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', 'isa_assembler')))



import os
import tempfile
from txt2hex import convert_txt_to_hex, _to_hex32

print("🚀 Iniciando test manual de txt2hex.py")

with tempfile.TemporaryDirectory() as tmpdir:
    input_txt = os.path.join(tmpdir, "program.txt")
    output_hex = os.path.join(tmpdir, "program.hex")

    # Crear archivo de entrada con varios formatos
    with open(input_txt, "w") as f:
        f.write("00000000000000000000000000000001\n")  # binario = 1
        f.write("42\n")                               # decimal = 42
        f.write("0x2A\n")                             # hex = 42
        f.write("15 # comentario\n")                  # decimal con comentario
        f.write("1010 ; otro comentario\n")           # binario = 10

    print(f"📄 Archivo de entrada creado en: {input_txt}")
    print("Contenido esperado:")
    print(" - Línea 1: binario → 1")
    print(" - Línea 2: decimal → 42")
    print(" - Línea 3: hex → 42")
    print(" - Línea 4: decimal con comentario → 15")
    print(" - Línea 5: binario con comentario → 10")

    # Ejecutar la conversión
    ints = convert_txt_to_hex(input_txt, output_hex)

    print("\n🔍 Verificando lista de enteros devuelta...")
    print(f"Resultado: {ints}")
    assert ints == [1, 42, 42, 15, 10], f"❌ Lista inesperada: {ints}"
    print("✅ Lista de enteros correcta")

    # Verificar archivo .hex generado
    with open(output_hex) as f:
        hex_lines = f.read().splitlines()

    print("\n🔍 Verificando archivo .hex generado...")
    for i, val in enumerate(ints):
        expected_hex = _to_hex32(val)
        print(f" - Instrucción {i+1}: valor={val}, esperado={expected_hex}, obtenido={hex_lines[i]}")
        assert hex_lines[i] == expected_hex, f"❌ Mismatch en línea {i+1}"

    print("\n✅ Archivo .hex correcto")

print("\n🎉 Todos los tests manuales de txt2hex.py pasaron correctamente")
