import sys
import os
from unittest.mock import Mock

# Asegurar rutas para imports locales
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.append(ROOT)

from pipeline.memory_stage import DataMemory, MemoryStage
from isa.isa_types import UInt64


def test_memory_vault_integration_verbose():
    """
    Test de integración detallado entre MemoryStage y VaultInterface (mockeada).

    Verifica:
     ✅ Delegación correcta de KVW/KVL/SGEN/SIGN a la bóveda (mock)
     ✅ Protección del rango de bóveda frente a accesos normales de memoria
     ✅ Propagación correcta de resultados de ALU (no-mem)
     ✅ Reporte final con estado de cada paso
    """

    GREEN = "\033[92m"
    RED = "\033[91m"
    RESET = "\033[0m"
    CHECK = f"{GREEN}✓{RESET}"
    FAIL = f"{RED}✗{RESET}"

    print("\n=== INICIO test_memory_vault_integration_verbose ===")

    # Crear DataMemory y MemoryStage con Vault mockeada
    data_mem = DataMemory()
    mock_vault = Mock()

    def vault_side_effect(opname, slot_idx, **kwargs):
        print(f"  [MOCK VAULT] execute_vault_operation(opname={opname}, slot_idx={slot_idx}, kwargs={kwargs})")
        if opname == 'KVW':
            return None
        if opname == 'KVL':
            return UInt64(0xCAFE)
        if opname in ('SGEN', 'SIGN'):
            return (UInt64(0x1111), UInt64(0x2222), UInt64(0x3333), UInt64(0x4444))
        return None

    mock_vault.execute_vault_operation.side_effect = vault_side_effect
    ms = MemoryStage(data_mem, vault_if=mock_vault)

    # Resultados parciales para resumen
    summary = []

    steps = [
        {
            'name': 'KVW - escribir llave KEY_0 con 0xCAFE',
            'ex_result': {'result': UInt64(0), 'latency': 1},
            'decoded': {
                'opcode_name': 'KVW',
                'operandos': {'vault_idx': 'KEY_0', 'rs2_val': UInt64(0xCAFE)},
                'control_signals': {'use_boveda': True}
            },
            'expect': {'vault_called': True, 'mem_unchanged': True}
        },
        {
            'name': 'KVL - leer llave KEY_0',
            'ex_result': {'result': UInt64(0), 'latency': 1},
            'decoded': {
                'opcode_name': 'KVL',
                'operandos': {'vault_idx': 'KEY_0'},
                'control_signals': {'use_boveda': True}
            },
            'expect': {'vault_called': True, 'returned_eq': UInt64(0xCAFE)}
        },
        {
            'name': 'SGEN - generar firma simulada',
            'ex_result': {'result': {'A': 1, 'B': 2, 'C': 3, 'D': 4}, 'latency': 2},
            'decoded': {
                'opcode_name': 'SGEN',
                'operandos': {'vault_idx': 'KEY_0', 'hash_state': {'A': 1, 'B': 2, 'C': 3, 'D': 4}},
                'control_signals': {'use_boveda': True}
            },
            'expect': {'vault_called': True, 'returned_is_sig': True}
        },
        {
            'name': 'LOAD - intento de leer rango de bóveda (debe fallar)',
            'ex_result': {'result': data_mem.vault_range[0], 'latency': 1},
            'decoded': {
                'opcode_name': 'LOAD',
                'operandos': {},
                'control_signals': {'use_boveda': False}
            },
            'expect': {'raises_permission_error': True}
        },
        {
            'name': 'ADD (no-mem) - resultado propagado sin bóveda',
            'ex_result': {'result': UInt64(0x1234), 'latency': 3},
            'decoded': {
                'opcode_name': 'ADD',
                'operandos': {},
                'control_signals': {'use_boveda': False}
            },
            'expect': {'propagated_result': UInt64(0x1234)}
        }
    ]

    for step in steps:
        print(f"\n--- STEP: {step['name']} ---")
        success = True
        ex_result = step['ex_result']
        decoded = step['decoded']

        try:
            if decoded['opcode_name'] == 'LOAD' and step['expect'].get('raises_permission_error'):
                try:
                    ms.execute(ex_result, decoded)
                    print("  [ERROR] No se lanzó PermissionError esperado.")
                    success = False
                except PermissionError as e:
                    print(f"  [OK] PermissionError capturado: {e}")
            else:
                out = ms.execute(ex_result, decoded)
                print(f"  MEM -> out = {out}")

                expect = step['expect']
                if expect.get('vault_called') and not mock_vault.execute_vault_operation.called:
                    print("  [ERROR] Se esperaba llamada a bóveda y no ocurrió.")
                    success = False
                if expect.get('mem_unchanged') and data_mem.memory != {}:
                    print(f"  [ERROR] Memoria general fue modificada: {data_mem.memory}")
                    success = False
                if 'returned_eq' in expect and out['result'] != expect['returned_eq']:
                    print(f"  [ERROR] Valor devuelto incorrecto: {out['result']} != {expect['returned_eq']}")
                    success = False
                if expect.get('returned_is_sig'):
                    sig = out['result']
                    if not (isinstance(sig, tuple) and len(sig) == 4):
                        print(f"  [ERROR] Firma inválida: {sig}")
                        success = False
                if 'propagated_result' in expect and out['result'] != expect['propagated_result']:
                    print(f"  [ERROR] Resultado propagado incorrecto: {out['result']}")
                    success = False

            summary.append((step['name'], success))

        except Exception as e:
            print(f"  [EXCEPCIÓN] {e}")
            summary.append((step['name'], False))

    # Resumen final
    print("\n=== RESUMEN FINAL ===")
    total_ok = 0
    for name, ok in summary:
        mark = CHECK if ok else FAIL
        print(f"  {mark} {name}")
        if ok:
            total_ok += 1

    total_calls = mock_vault.execute_vault_operation.call_count
    print(f"\nLlamadas totales a bóveda: {total_calls}")
    print(f"DataMemory metrics: {data_mem.get_metrics()}")

    all_passed = total_ok == len(summary)
    print(f"\nResultado global: {'✅ TODO OK' if all_passed else '❌ Fallos detectados'}")
    print("=== FIN test_memory_vault_integration_verbose ===\n")

    assert all_passed, f"Fallaron {len(summary) - total_ok} pasos del test"
    return True


if __name__ == "__main__":
    test_memory_vault_integration_verbose()
