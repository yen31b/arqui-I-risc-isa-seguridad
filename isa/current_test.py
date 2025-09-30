# main.py
from isa_types import UInt64, Vec4x64
from isa_definition import VAULT_SLOTS
from keyvault import KeyVault, VaultAccessError

def print_header(title: str):
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)

def main():
    # Crear bóveda
    vault = KeyVault()

    print_header("1. Inicialización de la Bóveda")
    print("Slots disponibles:", VAULT_SLOTS)
    print("Estado inicial:", vault.dump_vault(authorized=True))

    # Paso 1: Escribir una llave en KEY_0
    key_value = 0xDEADBEEFCAFEBABE
    print_header("2. Escritura de llave en KEY_0")
    try:
        vault.write_slot("KEY_0", key_value, authorized=True)
        print(f"Llave escrita en KEY_0: 0x{key_value:016X}")
    except VaultAccessError as e:
        print("ERROR:", e)

    print("Estado actual bóveda:", vault.dump_vault(authorized=True))

    # Paso 2: Definir un estado Vec4x64
    state = Vec4x64([
        UInt64(0x1111111111111111),
        UInt64(0x2222222222222222),
        UInt64(0x3333333333333333),
        UInt64(0x4444444444444444),
    ])
    print_header("3. Estado inicial Vec4x64")
    print(state)

    # Paso 3: Generar firma con la llave de KEY_0
    print_header("4. Generación de firma con SGEN")
    signature = vault.generate_signature("KEY_0", state)
    print("Firma generada:", signature)

    # Paso 4: Verificación (esperado vs obtenido)
    print_header("5. Verificación de resultado esperado vs obtenido")
    # CORRECCIÓN: usar indexación y int(...) en lugar de atributos inexistentes
    expected = Vec4x64([
        UInt64(int(state[0]) ^ key_value),
        UInt64(int(state[1]) ^ key_value),
        UInt64(int(state[2]) ^ key_value),
        UInt64(int(state[3]) ^ key_value),
    ])

    print("Esperado:", expected)
    print("Obtenido:", signature)

    # Comparar como listas de enteros (no usar .words/.value)
    expected_list = [int(expected[i]) for i in range(4)]
    signature_list = [int(signature[i]) for i in range(4)]
    print("Coinciden:", expected_list == signature_list)

    # Paso 5: Auditoría
    print_header("6. Auditoría de la bóveda")
    print(vault.get_audit_counters())

if __name__ == "__main__":
    main()
