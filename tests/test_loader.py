import os
import sys
import tempfile
import unittest

# Asegurar imports del proyecto
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.append(ROOT)

from compiler.isa_assembler.loader import select_file, _build_boot_image_from_bytes
from compiler.isa_assembler.loader import dump_signed_file
from pipeline.memory_stage import DataMemory, set_boot_image
from compiler.isa_assembler.assembler import Assembler
from pipeline.pipeline import Pipeline
from isa.isa_definition import VAULT_ADDR_RANGE
from isa.isa_types import Vec4x64, UInt64


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

    def test_signed_file_dump(self):
        # Probar volcado de archivo firmado
        data = b'\x01\x02\x03\x04' * 4  # 32 bytes
        path = self._write_temp_file(data)

        info = load_file_into_memory(self.mem, path=path, header_base=0, endian='big')
        blocks_base = info['blocks_base']

        # Escribir algo en la memoria para firmar
        self.mem.memory[blocks_base] = 0x1122334455667788

        # Volcar archivo firmado
        base, ext = os.path.splitext(path)
        signed_path = f"{base}.signed{ext}"
        dump_signed_file(self.mem, signed_path, header_base=0, endian='big', include_hash=True)

        # Leer el archivo firmado y verificar contenido
        with open(signed_path, 'rb') as f:
            signed_data = f.read()

        # El archivo firmado debe comenzar con el hash y luego los datos
        expected_prefix = b'\x88\x77\x66\x55\x44\x33\x22\x11'  # hash de 8 bytes
        self.assertTrue(signed_data.startswith(expected_prefix))

        os.remove(path)
        os.remove(signed_path)

def _fmt64(x: int) -> str:
    return f"0x{x:016X}"

def _read_vec4_from_mem(dm: DataMemory, base: int) -> Vec4x64:
    vals = [int(dm.memory.get(base + i*8, 0)) for i in range(4)]
    return Vec4x64(vals)

def _dump_signed_hex_file(bin_path: str, hex_path: str, max_bytes: int = 256):
    try:
        with open(bin_path, "rb") as f:
            data = f.read()
        with open(hex_path, "w", encoding="utf-8") as h:
            h.write(f"# Hex dump de {os.path.basename(bin_path)} ({len(data)} bytes)\n")
            h.write("# Offset: 16 bytes por línea\n")
            for off in range(0, min(len(data), max_bytes), 16):
                chunk = data[off:off+16]
                h.write(f"{off:08x}: " + " ".join(f"{b:02x}" for b in chunk) + "\n")
            if len(data) > max_bytes:
                h.write(f"... ({len(data)-max_bytes} bytes omitidos)\n")
        print(f"[test_loader] Hex dump escrito en: {hex_path}")
    except Exception as e:
        print(f"[test_loader] ⚠️ No se pudo escribir hex dump: {e}")

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
    print("  4 → Ver sólo memoria")
    print("  q → Salir del modo debug (sin continuar)")
    while True:
        choice = input("Opción (1/2/3/4/q): ").strip().lower()
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
        elif choice == '4':
            _dump_memory(p.data_mem, header_base=0, max_blocks=32)
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

    # Volcar archivo firmado junto al original
    try:
        base, ext = os.path.splitext(path)
        out_path = f"{base}.signed{ext or ''}"
        dump_signed_file(p.data_mem, out_path, header_base=0, endian="big", include_hash=True)
        print(f"[test_loader] Archivo firmado escrito en: {out_path}")

        # Crear un dump .hex para inspección humana
        hex_path = f"{base}.signed{ext or ''}.hex"
        _dump_signed_hex_file(out_path, hex_path, max_bytes=256)

        # Verificación programática de la firma usando la bóveda
        mem = p.data_mem.memory
        cnt = int(mem.get(0, 0))
        bbase = int(mem.get(8, 0))
        hash_base = bbase + cnt * 8
        sig_base = hash_base + 32
        hash_vec = _read_vec4_from_mem(p.data_mem, hash_base)
        sig_vec = _read_vec4_from_mem(p.data_mem, sig_base)
        print("\n[test_loader] Hash (memoria) y firma (memoria):")
        for i, name in enumerate(("A","B","C","D")):
            hv = int(hash_vec[i]); sv = int(sig_vec[i])
            print(f"  H[{name}] = {_fmt64(hv)}   S[{name}] = {_fmt64(sv)}")

        # Usar slot 0 (KEY_0) inicializado por el Pipeline para verificar
        verified = bool(p.vault_if.execute_vault_operation('VERIFY', 0, state=hash_vec, signature=sig_vec))
        print(f"\n[test_loader] Resultado VERIFY (KEY_0 vs hash_mem y sig_mem): {'OK' if verified else 'FAIL'}")
        if not verified:
            print("  ⚠️ Si falla, confirma que KEY_0 está inicializada y que SGEN usó el mismo slot.")

    except Exception as e:
        print(f"[test_loader] ⚠️ No se pudo generar archivo firmado: {e}")

if __name__ == "__main__":
    main()
