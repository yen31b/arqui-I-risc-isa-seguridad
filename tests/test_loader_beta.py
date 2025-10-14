import os
import sys
import tempfile
import unittest

# Asegurar imports de paquete
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from compiler.isa_assembler.loader import load_file_into_memory, select_file, _build_boot_image_from_bytes
from pipeline.memory_stage import DataMemory, set_boot_image
from compiler.isa_assembler.assembler import Assembler
from pipeline.pipeline import Pipeline
from isa.isa_definition import VAULT_ADDR_RANGE


class LoaderIntegrationTests(unittest.TestCase):
    def setUp(self):
        # Memoria de datos fresca por test
        self.mem = DataMemory(vault_range=VAULT_ADDR_RANGE)

    def _write_temp_file(self, data: bytes) -> str:
        fd, path = tempfile.mkstemp()
        os.close(fd)
        with open(path, 'wb') as f:
            f.write(data)
        return path

    def test_load_minimal_file_into_memory(self):
        # Archivo de 16 bytes exactos = 2 bloques de 64 bits
        data = b'\x00\x00\x00\x00\x00\x00\x00\x01' + b'\x00\x00\x00\x00\x00\x00\x00\x02'
        path = self._write_temp_file(data)

        info = load_file_into_memory(self.mem, path=path, header_base=0, endian='big')

        # count = 2, blocks_base = 0x10 (header ocupa 16 bytes)
        self.assertEqual(self.mem.memory.get(0), 2)
        self.assertEqual(self.mem.memory.get(8), 16)
        self.assertEqual(info['count'], 2)
        self.assertEqual(info['header_base'], 0)
        self.assertEqual(info['blocks_base'], 16)

        # Verificar bloques
        self.assertEqual(self.mem.memory.get(16), int.from_bytes(data[0:8], 'big'))
        self.assertEqual(self.mem.memory.get(24), int.from_bytes(data[8:16], 'big'))

        # No debe escribir dentro de VAULT_ADDR_RANGE
        vault_lo, vault_hi = VAULT_ADDR_RANGE
        for addr in [0, 8, 16, 24]:
            self.assertFalse(vault_lo <= addr <= vault_hi)

        os.remove(path)

    def test_relocation_avoids_vault_range(self):
        # Forzar que los bloques crucen 0x1000: generar 520 bloques (~4160 bytes)
        block_count = 520
        data = bytearray()
        for i in range(block_count):
            data += int(i).to_bytes(8, 'big')
        path = self._write_temp_file(bytes(data))

        info = load_file_into_memory(self.mem, path=path, header_base=0, endian='big')

        # Debe haber reubicación de blocks_base fuera del rango de bóveda (>= 0x2000)
        vault_lo, vault_hi = VAULT_ADDR_RANGE
        self.assertGreaterEqual(info['blocks_base'], (vault_hi + 8) // 8 * 8)

        # Ninguna dirección de bloque debe caer dentro del rango protegido
        for i in range(block_count):
            addr = info['blocks_base'] + i * 8
            self.assertFalse(vault_lo <= addr <= vault_hi, f"addr 0x{addr:04x} cayó en rango de bóveda")

        os.remove(path)

    def test_boot_image_preload(self):
        # Construir imagen desde bytes y registrar boot image
        data = b'\xaa' * 24  # 3 bloques
        image = _build_boot_image_from_bytes(data, header_base=0, endian='big')
        set_boot_image(image)

        # Nueva DataMemory debe precargar el contenido
        fresh = DataMemory(vault_range=VAULT_ADDR_RANGE)
        # Debe contener al menos header y puntero
        self.assertIn(0, fresh.memory)
        self.assertIn(8, fresh.memory)
        count = fresh.memory[0]
        blocks_base = fresh.memory[8]
        self.assertEqual(count, 3)
        # Validar primer bloque
        first_block = int.from_bytes(b'\xaa' * 8, 'big')
        self.assertEqual(fresh.memory.get(blocks_base), first_block)

    def test_loader_end_to_end(self):
        print("[test_loader] Selecciona el archivo a cargar (se abrirá un diálogo)...")
        path = select_file()
        print(f"[test_loader] Archivo elegido: {path}")

        with open(path, "rb") as f:
            raw = f.read()

        # Construir imagen de arranque (header + puntero + bloques) con padding
        image = _build_boot_image_from_bytes(raw, header_base=0, endian="big")
        count = image.get(0, 0)
        blocks_base = image.get(8, 0)
        print(f"[test_loader] Imagen de arranque construida:")
        print(f"  - count        @0x0000 = {count}")
        print(f"  - blocks_base  @0x0008 = 0x{blocks_base:04X}")
        print(f"  - VAULT_ADDR_RANGE = {VAULT_ADDR_RANGE}")

        # Registrar boot image global para que DataMemory la precargue
        set_boot_image(image)

        # Verificar precarga en una DataMemory "en frío"
        dm = DataMemory(vault_range=VAULT_ADDR_RANGE)
        assert dm.memory.get(0) == count, "Header 'count' no coincide"
        assert dm.memory.get(8) == blocks_base, "Header 'blocks_base' no coincide"

        # Mostrar primeros bloques de DataMemory
        print("\n[test_loader] Dump de DataMemory (primeros 8 bloques o todos si menos):")
        max_show = min(count, 8)
        for i in range(max_show):
            addr = blocks_base + i * 8
            val = dm.memory.get(addr, 0)
            print(f"  [{addr:04X}] = {_fmt64(val)}")
        if count > max_show:
            print(f"  ... ({count - max_show} bloques más)")

        # Ensamblar y ejecutar hast.s para validar el flujo end-to-end
        #Assembly\hast.s
        asm_path = os.path.join("Assembly", "hast.s")
        if not os.path.exists(asm_path):
            print(f"[test_loader] ADVERTENCIA: No se encontró {asm_path}. Se omitirá la ejecución del pipeline.")
            return

        print("\n[test_loader] Ensamblando y ejecutando Assembly\\hast.s sobre un Pipeline...")
        words = Assembler().assemble_file(asm_path)
        p = Pipeline(words)

        # Ejecutar en modo batch simple (sin menú interactivo)
        total = len(p.instr_mem.instructions)
        for _ in range(total):
            try:
                p.step()
            except IndexError:
                break
            except PermissionError as e:
                print(f"[test_loader] 🛑 Violación de seguridad durante ejecución: {e}")
                break
            except Exception as e:
                print(f"[test_loader] ❌ Error durante ejecución: {e}")
                break

        # Mostrar registros finales
        regs = p.rf.dump_registers()
        print("\n[test_loader] Registros finales (todos):")
        for name in sorted(regs.keys(), key=lambda k: (k not in ("PC", "SR"), k)):
            print(f"  - {name}: 0x{regs[name]:016x}")

        # Validaciones suaves post-ejecución (si el programa leyó header/ptr)
        # Nota: hast.s espera LOAD R24, 0(R0) y LOAD R21, 8(R0)
        if "R24" in regs and "R21" in regs:
            print("\n[test_loader] Verificación de registros de cabecera que debería haber leído hast.s:")
            print(f"  - R24 (count):           0x{regs['R24']:016x} {'OK' if regs['R24']==count else 'MISMATCH'}")
            print(f"  - R21 (blocks_base ptr): 0x{regs['R21']:016x} {'OK' if regs['R21']==blocks_base else 'MISMATCH'}")

        # Resumen final
        print("\n[test_loader] Resumen:")
        print(f"  - Archivo: {os.path.basename(path)}")
        print(f"  - Bloques cargados: {count}")
        print(f"  - Header en 0x0000/0x0008; blocks_base={_fmt64(blocks_base)}")
        print("  - Si R24/R21 coinciden, y HASH_FINAL produjo valores en R20..R23, el flujo está OK.")


def _fmt64(x: int) -> str:
    return f"0x{x:016X}"


if __name__ == '__main__':
    unittest.main()
