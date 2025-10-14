# test_vault_interface.py
import sys
import os
CUR_DIR = os.path.abspath(os.path.dirname(__file__))
ROOT = os.path.abspath(os.path.join(CUR_DIR, '..'))
# Quitar el dir actual (vault/) para evitar que 'vault.py' haga sombra al paquete 'vault'
try:
    while CUR_DIR in sys.path:
        sys.path.remove(CUR_DIR)
except Exception:
    pass
# Anteponer la raíz del proyecto
if ROOT in sys.path:
    sys.path.remove(ROOT)
sys.path.insert(0, ROOT)
# Importar siempre desde el paquete
from vault.vault_interface import VaultInterface

from isa.isa_types import Vec4x64

def main():
    vi = VaultInterface()

    # 1. Escribir una llave en el slot 0 (KEY_0) con KVW
    print(">>> Escribiendo llave en KEY_0 con KVW")
    vi.execute_vault_operation("KVW", 0, value=0x1122334455667788)

    # 2. Usar KVOP para aplicar una operación controlada (xor_scalar)
    print(">>> Usando KVOP en KEY_0 con xor_scalar")
    result = vi.execute_vault_operation("KVOP", 0, action="xor_scalar", scalar=0xAA)
    print("Resultado KVOP xor_scalar:", hex(int(result)))

    # 3. Generar una firma con SGEN
    print(">>> Generando firma con SGEN en KEY_0")
    state = Vec4x64([1, 2, 3, 4])
    sig = vi.execute_vault_operation("SGEN", 0, state=state)
    print("Firma generada:", sig)

    # 4. Mostrar reporte de seguridad
    print("\n--- Reporte de seguridad ---")
    report = vi.get_security_report()
    for k, v in report.items():
        print(f"{k}: {v}")

if __name__ == "__main__":
    main()
