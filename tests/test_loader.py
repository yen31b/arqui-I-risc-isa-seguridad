import os
import sys
import tempfile
import unittest

# Asegurar imports del proyecto
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.append(ROOT)

from compiler.isa_assembler.loader import select_file, _build_boot_image_from_bytes
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
        print(f"[test_loader] Imagen preparada: count={count}, blocks_base=0x{int(blocks_base):04X}")

        # Registrar boot image global para precarga en DataMemory
        set_boot_image(image)

        # Verificar precarga rápida
        dm_probe = DataMemory(vault_range=VAULT_ADDR_RANGE)
        assert dm_probe.memory.get(0) == count, "Header 'count' no coincide en DataMemory"
        assert dm_probe.memory.get(8) == blocks_base, "Header 'blocks_base' no coincide en DataMemory"

        # Ensamblar y crear Pipeline con hast.s
        asm_path = os.path.join(ROOT, "Assembly", "hast.s")
        if not os.path.exists(asm_path):
            print(f"[test_loader] ADVERTENCIA: No se encontró {asm_path}. Saliendo.")
            return
        print("[test_loader] Ensamblando Assembly\\hast.s ...")
        words = Assembler().assemble_file(asm_path)
        p = Pipeline(words)

        # Elegir modo de ejecución
        print("\n[test_loader] Selecciona modo de ejecución:")
        print("  1 → Normal (ejecutar hasta el final)")
        print("  2 → Debug (paso a paso)")
        mode = input("Opción (1/2): ").strip()
        if mode == '2':
            # Mostrar estado inicial
            _dump_memory(p.data_mem, header_base=0, max_blocks=8)
            _dump_registers(p)
            _run_debug(p)
        else:
            _run_batch(p)

        # Resumen final breve
        print("\n[test_loader] Resumen:")
        print(f"  - Archivo: {os.path.basename(path)}")
        print(f"  - Bloques cargados: {int(count)}")
        print(f"  - Header en 0x0000/0x0008; blocks_base={_fmt64(int(blocks_base))}")
        print("  - Verifica que R24/R21 hayan sido leídos en hast.s y que HASH_FINAL actualice R20..R23.")

def _fmt64(x: int) -> str:
    return f"0x{x:016X}"

def _dump_memory(dm: DataMemory, *, header_base: int = 0, max_blocks: int = 8):
    count = dm.memory.get(header_base, 0)
    blocks_base = dm.memory.get(header_base + 8, 0)
    print(f"\n[test_loader] DataMemory (header + primeros bloques):")
    print(f"  - [0x{header_base:04X}] count       = {count}")
    print(f"  - [0x{header_base+8:04X}] blocks_ptr = 0x{blocks_base:04X}")
    if not count or not blocks_base:
        print("  (header incompleto o sin datos)")
        return
    to_show = min(int(count), max_blocks)
    for i in range(to_show):
        addr = int(blocks_base) + i * 8
        val = dm.memory.get(addr, 0)
        print(f"  - [{addr:04X}] = {_fmt64(val)}")
    if count > to_show:
        print(f"  ... ({int(count) - to_show} bloques más)")
    print(f"  - VAULT_ADDR_RANGE = {VAULT_ADDR_RANGE}")

def _dump_registers(p: Pipeline):
    regs = p.rf.dump_registers()
    print("\n[test_loader] Registros (todos):")
    for name in sorted(regs.keys(), key=lambda k: (k not in ("PC", "SR"), k)):
        print(f"  - {name}: 0x{regs[name]:016x}")

def _run_batch(p: Pipeline):
    total = len(p.instr_mem.instructions)
    for _ in range(total):
        try:
            p.step()
        except IndexError:
            break
        except PermissionError as e:
            print(f"[test_loader] 🛑 Violación de seguridad: {e}")
            break
        except Exception as e:
            print(f"[test_loader] ❌ Error durante ejecución: {e}")
            break
    # Reporte final
    p._print_final_report()

def _run_debug(p: Pipeline):
    print("\n[test_loader] Modo DEBUG — opciones:")
    print("  1 → Avanzar 1 ciclo")
    print("  2 → Ejecutar hasta el final (salir del modo debug)")
    print("  3 → Ver registros y memoria")
    print("  q → Salir del modo debug (sin continuar)")
    while True:
        choice = input("Opción (1/2/3/q): ").strip().lower()
        if choice == '1':
            try:
                p.step()
            except IndexError:
                print("[test_loader] ✅ Fin de instrucciones.")
                p._print_final_report()
                break
            except PermissionError as e:
                print(f"[test_loader] 🛑 Violación de seguridad: {e}")
                break
            except Exception as e:
                print(f"[test_loader] ❌ Error: {e}")
                break
        elif choice == '2':
            _run_batch(p)
            break
        elif choice == '3':
            _dump_registers(p)
            _dump_memory(p.data_mem, header_base=0, max_blocks=8)
        elif choice == 'q':
            print("[test_loader] Saliendo de modo debug sin continuar.")
            break
        else:
            print("⚠️  Opción no válida.")

def main():
    print("[test_loader] Selecciona el archivo a cargar (se abrirá un diálogo)...")
    path = select_file()
    print(f"[test_loader] Archivo elegido: {path}")

    with open(path, "rb") as f:
        raw = f.read()

    # Construir imagen de arranque (header + puntero + bloques) con padding y respetando VAULT_ADDR_RANGE
    image = _build_boot_image_from_bytes(raw, header_base=0, endian="big")
    count = image.get(0, 0)
    blocks_base = image.get(8, 0)
    print(f"[test_loader] Imagen preparada: count={count}, blocks_base=0x{int(blocks_base):04X}")

    # Registrar boot image global para precarga en DataMemory
    set_boot_image(image)

    # Verificar precarga rápida
    dm_probe = DataMemory(vault_range=VAULT_ADDR_RANGE)
    assert dm_probe.memory.get(0) == count, "Header 'count' no coincide en DataMemory"
    assert dm_probe.memory.get(8) == blocks_base, "Header 'blocks_base' no coincide en DataMemory"

    # Ensamblar y crear Pipeline con hast.s
    asm_path = os.path.join(ROOT, "Assembly", "hast.s")
    if not os.path.exists(asm_path):
        print(f"[test_loader] ADVERTENCIA: No se encontró {asm_path}. Saliendo.")
        return
    print("[test_loader] Ensamblando Assembly\\hast.s ...")
    words = Assembler().assemble_file(asm_path)
    p = Pipeline(words)

    # Elegir modo de ejecución
    print("\n[test_loader] Selecciona modo de ejecución:")
    print("  1 → Normal (ejecutar hasta el final)")
    print("  2 → Debug (paso a paso)")
    mode = input("Opción (1/2): ").strip()
    if mode == '2':
        # Mostrar estado inicial
        _dump_memory(p.data_mem, header_base=0, max_blocks=8)
        _dump_registers(p)
        _run_debug(p)
    else:
        _run_batch(p)

    # Resumen final breve
    print("\n[test_loader] Resumen:")
    print(f"  - Archivo: {os.path.basename(path)}")
    print(f"  - Bloques cargados: {int(count)}")
    print(f"  - Header en 0x0000/0x0008; blocks_base={_fmt64(int(blocks_base))}")
    print("  - Verifica que R24/R21 hayan sido leídos en hast.s y que HASH_FINAL actualice R20..R23.")

if __name__ == "__main__":
    main()
