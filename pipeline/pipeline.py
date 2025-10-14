# pipeline.py

"""
Simulación del pipeline básico: IF → ID → EX
Responsabilidad:
 - Coordinar el flujo entre etapas.
 - Ejecutar instrucciones paso a paso.
 - Recolectar métricas globales.
"""
import io
import contextlib

from vault.vault_interface import VaultInterface
from isa.isa_definition import INSTRUCTION_FORMAT_DECISION, TOYMDMA_CONSTANTS, VAULT_SLOTS
from isa.isa_types import UInt64, Vec4x64
from isa.register_file import register_file
from .fetch_stage import InstructionMemory, FetchStage
from .decode_stage import DecodeStage
from .execute_stage import ExecuteStage
from .memory_stage import MemoryStage, DataMemory
from .writeback_stage import WriteBackStage

class Pipeline:
    def __init__(self, instructions):
        self.rf = register_file()
        self.instr_mem = InstructionMemory(instructions)
        self.data_mem = DataMemory(vault_range=(0x1000, 0x1FFF))

        # Interfaz única de bóveda para todo el pipeline
        self.vault_if = VaultInterface()

        # --- Inicializar IVs de hash en la bóveda (HASH_A..HASH_D) usando constantes --
        # Evita violaciones cuando HASH_INIT intenta leer los IVs.
        try:
            for suffix in ('A', 'B', 'C', 'D'):
                slot_name = f"HASH_{suffix}"
                if slot_name in VAULT_SLOTS:
                    idx = VAULT_SLOTS[slot_name]
                    const_key = f"INITIAL_{suffix}"
                    val = TOYMDMA_CONSTANTS.get(const_key)
                    if val is not None:
                        # KVW vía VaultInterface escribe el slot (autorizado por VaultInterface)
                        self.vault_if.execute_vault_operation('KVW', idx, value=val)
                        print(f"  🔐 PIPELINE: Inicializado slot {slot_name} (idx={idx}) <- 0x{int(val):016x}")
        except Exception as e:
            # No bloquear creación de pipeline si algo falla; solo advertir.
            print(f"  ⚠️ PIPELINE: No se pudieron inicializar IVs en bóveda: {e}")

        self.fetch = FetchStage(self.rf, self.instr_mem)
        self.decode = DecodeStage(self.rf)
        # pasar vault_if a las etapas que lo necesitan
        self.execute = ExecuteStage(vault_if=self.vault_if, rf=self.rf)
        self.memory = MemoryStage(self.data_mem, vault_if=self.vault_if)
        self.writeback = WriteBackStage(self.rf)

        self.completed = []
        self.cycle = 0

    def step(self):
        """Ejecuta un ciclo completo: IF -> ID -> EX -> MEM -> WB"""
        print(f"\n🔄 Ciclo {self.cycle + 1}")
        instr = self.fetch.step()
        print(f"→ IF: instrucción = 0x{instr:08x}")

        decoded = self.decode.decode(instr)
        print(f"→ ID: opcode = {decoded['opcode_name']}, formato = {decoded['format_type']}")

        # preparar operandos
        self._read_operands(decoded)

        # Execute
        ex_result = self.execute.execute(decoded)
        print(f"→ EX: resultado = {ex_result['result']}, latencia = {ex_result['latency']}")

        # --- NUEVO: manejar branches/jumps decididos en EX ---
        if ex_result.get('branch_taken'):
            target = ex_result.get('target_pc')
            if target is not None:
                # target puede ser UInt64 o int; aseguramos int al escribir PC
                new_pc = int(target)
                # Actualiza PC para el próximo fetch (efecto inmediato)
                self.rf.write('PC', new_pc)
                print(f"  🔧 EX → PIPELINE: Branch taken. PC actualizado a 0x{new_pc:016x}")
            else:
                print("  🔧 EX → PIPELINE: Branch taken pero target_pc es None (no cambio de PC).")
        # --- FIN NUEVO manejo de branch ---

        # Memory stage
        mem_result = self.memory.execute(ex_result, decoded)
        mem_access_type = "BÓVEDA" if mem_result.get('vault_accessed') else ("MEMORIA" if mem_result.get('memory_accessed') else "NINGUNO")
        print(f"→ MEM: acceso = {mem_access_type}, latencia = {mem_result.get('latency')}")

        # Writeback
        wb_result = self.writeback.execute(mem_result, decoded)
        if wb_result.get('written'):
            val = wb_result.get('value')
            rd = wb_result.get('register')
            if isinstance(val, Vec4x64):
                print(f"→ WB: R{rd}-R{rd+3} ← FIRMA (vector)")
            else:
                print(f"→ WB: R{rd} ← {val}")

        # Save completed
        self.completed.append({'instr': instr, 'decoded': decoded, 'ex_result': ex_result, 'mem_result': mem_result})
        self.cycle += 1

    def _read_operands(self, decoded):
        """Lee operandos desde el banco de registros - MEJORADO"""
        ops = decoded.get('operandos', {})

        print(f"  📖 Leyendo operandos para {decoded['opcode_name']}:")
        opcode = decoded.get('opcode_name')

        # Leer valores de registros source
        if 'rs1' in ops and ops['rs1'] is not None:
            reg_name = f"R{ops['rs1']}"
            ops['rs1_val'] = self.rf.read(reg_name)
            print(f"    {reg_name} = {ops['rs1_val']}")

        if 'rs2' in ops and ops['rs2'] is not None:
            reg_name = f"R{ops['rs2']}"
            ops['rs2_val'] = self.rf.read(reg_name)
            print(f"    {reg_name} = {ops['rs2_val']}")

        if 'imm' in ops and ops['imm'] is not None:
            ops['imm'] = ops.get('imm')
            print(f"    imm = {ops['imm']} (0x{ops['imm']:x})")

        # --- Construir Vec4x64 desde registro base para hash/signature ---
        try:
            if opcode in ('SGEN', 'SIGN'):
                # estado hash en rs1 (registro base)
                if 'rs1' in ops and ops['rs1'] is not None:
                    base = int(ops['rs1'])
                    state_vec = Vec4x64([
                        self.rf.read(f"R{base + i}") for i in range(4)
                    ])
                    ops['hash_state'] = state_vec
                    print(f"    hash_state (R{base}..R{base+3}) = {state_vec}")

            elif opcode == 'VERIFY':
                # signature en rs1 (registro base)
                if 'rs1' in ops and ops['rs1'] is not None:
                    base = int(ops['rs1'])
                    sig_vec = Vec4x64([
                        self.rf.read(f"R{base + i}") for i in range(4)
                    ])
                    ops['signature'] = sig_vec
                    # también dejar rs1_val con el primer componente por compatibilidad
                    ops['rs1_val'] = self.rf.read(f"R{base}")
                    print(f"    signature (R{base}..R{base+3}) = {sig_vec}")
        except Exception as e:
            # No fatal; dejamos que EX/MEM manejen la ausencia del vector
            print(f"    ⚠️  No se pudo construir Vec4x64 desde registro base: {e}")

    def _read_hash_state(self):
        """Lee estado hash en R4..R7 y retorna Vec4x64."""
        a = self.rf.read('R4')
        b = self.rf.read('R5')
        c = self.rf.read('R6')
        d = self.rf.read('R7')
        return Vec4x64([a, b, c, d])

    def run(self, max_cycles=None):
        """Modo interactivo:
           1 → Avanzar un ciclo
           2 → Ejecutar hasta fin (sin detalle)
           3 → Mostrar todos los registros
           q → Salir
        """
        print("🚦 Modo interactivo:")
        print("   1 → Avanzar un ciclo")
        print("   2 → Ejecutar hasta el final (sin detalle)")
        print("   3 → Mostrar todos los registros actuales")
        print("   q → Salir\n")

        while True:
            choice = input("Opción (1/2/3/q): ").strip()
            if choice == '1':
                try:
                    self.step()
                except IndexError:
                    print("✅ Fin de instrucciones.")
                    break
                except PermissionError as e:
                    print(f"🛑 VIOLACIÓN DE SEGURIDAD: {e}")
                    break
                except Exception as e:
                    print(f"❌ Error en ciclo {self.cycle+1}: {e}")
                    break

            elif choice == '2':
                # Calcula cuántos ciclos faltan
                total_instr = len(self.instr_mem.instructions)
                max_cycles = max_cycles or total_instr

                # Redirigimos toda la salida de print() a un buffer
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    for _ in range(max_cycles):
                        try:
                            self.step()
                        except IndexError:
                            # fin normal
                            break
                        except PermissionError as e:
                            # violación de seguridad
                            break
                        except Exception:
                            # cualquier otro error corta el bucle
                            break

                # Sólo un mensaje al final
                print(f"\n🚀 Ejecución completa: {self.cycle} ciclos ejecutados, "
                      f"{len(self.completed)} instrucciones procesadas.")
                """
                # Reutilizamos run() para terminar y mostrar reporte final
                instr_size = INSTRUCTION_FORMAT_DECISION['width_bits'] // 8
                total_instr = len(self.instr_mem.instructions)
                max_cycles = max_cycles or total_instr
                #print("🚀 Iniciando pipeline...")
                for i in range(max_cycles):
                    try:
                        self.step()
                    except IndexError:
                        print("✅ Fin de instrucciones.")
                        break
                    except PermissionError as e:
                        print(f"🛑 VIOLACIÓN DE SEGURIDAD: {e}")
                        break
                    except Exception as e:
                        print(f"❌ Error en ciclo {i+1}: {e}")
                        break
                        """
                # Mostrar todos los registros (incluso ceros)
                regs = self.rf.dump_registers()
                print("\n📋 Estado completo de registros:")
                for name, val in regs.items():
                    print(f"   - {name}: 0x{val:016x}")
                print("")  # línea en blanco de separación
                
                self._print_final_report()
                break

            elif choice == '3':
                # Mostrar todos los registros (incluso ceros)
                regs = self.rf.dump_registers()
                print("\n📋 Estado completo de registros:")
                for name, val in regs.items():
                    print(f"   - {name}: 0x{val:016x}")
                print("")  # línea en blanco de separación

            elif choice.lower() == 'q':
                print("✋ Modo interactivo finalizado.")
                break

            else:
                print("⚠️  Opción no válida. Ingresa 1, 2 o q.\n")

    def _print_final_report(self):
        print(f"\n{'='*60}")
        print("📊 EJECUCIÓN COMPLETADA")
        print(f"{'='*60}")
        print(f"   Ciclos totales: {self.cycle}")
        print(f"   Instrucciones procesadas: {len(self.completed)}")
        mem_metrics = self.memory.get_metrics()
        print(f"\n🛡️  MÉTRICAS DE SEGURIDAD (DataMemory):")
        print(f"   - Accesos a memoria: {mem_metrics.get('mem_accesses', 0)}")
        print(f"   - Accesos a bóveda (DataMemory view): {mem_metrics.get('vault_accesses', 0)}")
        print(f"   - Violaciones bloqueadas: {mem_metrics.get('security_blocks', 0)}")

        # Añadir métricas de VaultInterface (si existe)
        try:
            if self.vault_if:
                vrep = self.vault_if.get_security_report()
                print(f"\n🔐 MÉTRICAS DE BÓVEDA (VaultInterface):")
                print(f"   - Vault ops (invocaciones): {vrep.get('vault_ops', 0)}")
                print(f"   - Vault reads: {vrep.get('vault_reads', 0)}")
                print(f"   - Vault writes: {vrep.get('vault_writes', 0)}")
                print(f"   - Vault atomic ops: {vrep.get('atomic_operations', 0)}")
                print(f"   - Vault violations: {vrep.get('vault_violations', vrep.get('security_violations',0))}")
        except Exception as e:
            print(f"   ⚠️  No se pudo obtener reporte de bóveda: {e}")

        print(f"\n💾 REGISTROS FINALES (solo no-cero):")
        regs = self.rf.dump_registers()
        non_zero_regs = {k: v for k, v in regs.items() if (k.startswith('R') and v != 0) or k in ['PC', 'SR']}
        for name, value in non_zero_regs.items():
            print(f"   - {name}: 0x{value:016x}")

    def get_metrics(self):
        return {
            'fetch': self.fetch.get_metrics(),
            'decode': self.decode.get_metrics(),
            'execute': self.execute.get_metrics(),
            'memory': self.memory.get_metrics(),
            'writeback': self.writeback.get_metrics(),
            'total_cycles': self.cycle,
            'instructions_completed': len(self.completed),
        }

    def load_test_program(self):
        """Carga un pequeño programa de prueba en instr_mem (ejemplo)."""
        from isa_definition import encode_instruction, OPCODES
        test_program = [
            encode_instruction('I_TYPE', opcode=OPCODES['ADDI'], rd=1, rs1=0, imm=0x100),
            encode_instruction('I_TYPE', opcode=OPCODES['ADDI'], rd=2, rs1=0, imm=0x200),
            encode_instruction('R_TYPE', opcode=OPCODES['ADD'], rd=3, rs1=1, rs2=2, funct=0),
        ]
        self.instr_mem.instructions = test_program
        self.rf.write('PC', 0)
        print("Programa de prueba cargado.")
    def get_cycle(self):
        """Retorna el número de ciclos ejecutados."""
        return self.cycle
