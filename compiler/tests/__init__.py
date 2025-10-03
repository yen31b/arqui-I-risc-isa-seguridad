import sys
from pathlib import Path

# Aseguramos que la carpeta src/ esté en el path durante las pruebas
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
