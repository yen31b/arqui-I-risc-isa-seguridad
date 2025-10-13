# execute_stage.py

"""
Etapa EX (Execute) del pipeline.
Responsabilidad:
 - Ejecutar operaciones aritméticas, lógicas, modulares, no lineales, y señales de bóveda.
 - Recibir operandos y señales de control desde la etapa ID.
 - Retornar resultado para MEM/WB y métricas de ejecución.
"""
from vault.vault_interface import VaultInterface
from isa.isa_types import UInt64, Vec4x64
from isa.hash_accel import mixmul, modadd, nonlin
from isa.isa_definition import TOYMDMA_CONSTANTS

class ExecuteStage:
    def __init__(self, vault_if: VaultInterface | None = None, rf = None):
        self.metrics = {
            'exec_count': 0,
            'cycles': 0,
            'op_latency': {},
        }
        # Interfaz a la bóveda (puede ser None en tests unitarios simples)
        self.vault_if = vault_if
        # Referencia opcional al banco de registros (permitir lecturas desde EX)
        self.rf = rf

    def _require_rf(self, instr_name):
        if self.rf is None:
            raise RuntimeError(f"Banco de registros (rf) requerido para instrucción {instr_name} pero no está configurado.")

    def execute(self, decoded_instr):
        """
        Ejecuta la operación indicada por la instrucción decodificada.
        """
        opcode = decoded_instr.get('opcode_name')
        ops = decoded_instr.get('operandos', {})
        ctrl = decoded_instr.get('control_signals', {})
        result = None
        latency = 1

        # DEBUG: Mostrar qué operandos tenemos
        print(f"  🔧 EX: Operandos disponibles: {list(ops.keys())}")

        # Extraer operandos (fall back a 0 si no existen)
        rs1_val = ops.get('rs1_val', ops.get('rs1', 0))
        rs2_val = ops.get('rs2_val', ops.get('rs2', 0))
        imm_val = ops.get('imm', 0)

        # Convertir a enteros de forma simple y robusta
        try:
            a_val = int(rs1_val)
        except Exception:
            a_val = 0
        try:
            b_val = int(rs2_val)
        except Exception:
            b_val = 0
        try:
            imm = int(imm_val)
        except Exception:
            imm = 0

        print(f"  🔧 EX: a_val={a_val}, b_val={b_val}, imm={imm}")

        # Señal de bóveda por defecto
        vault_signal = False

        # Si la instrucción requiere acceso a la bóveda, delegar
        if ctrl.get('use_boveda', False):
            if not self.vault_if:
                raise RuntimeError("VaultInterface no configurada en ExecuteStage para instrucción de bóveda")

            slot_idx = ops.get('vault_idx')
            try:
                if opcode in ('KVW', 'VSTORE'):
                    # escribir slot: valor provisto en rs1_val o imm
                    value = ops.get('rs1_val', ops.get('value', 0))
                    self.vault_if.execute_vault_operation('KVW', slot_idx, value=value)
                    result = None
                    latency = 5

                elif opcode in ('KVL', 'VLOAD'):
                    # leer slot (operación controlada)
                    result = self.vault_if.execute_vault_operation('KVL', slot_idx)
                    latency = 3

                elif opcode == 'KVOP':
                    # operación específica sobre slot
                    result = self.vault_if.execute_vault_operation('KVOP', slot_idx, action=ops.get('action'), scalar=ops.get('scalar'), state=ops.get('state'))
                    latency = 6

                elif opcode in ('SGEN', 'SIGN'):
                    # generar firma: se espera `hash_state` o un Vec4x64 en ops
                    state = ops.get('hash_state') or ops.get('rs1_val') or ops.get('state')
                    result = self.vault_if.execute_vault_operation('SGEN', slot_idx, state=state)
                    latency = 8

                elif opcode == 'VINIT':
                    # Inicializar slot con valor inmediato o rs1_val (autorizado)
                    value = ops.get('rs1_val', ops.get('imm', 0))
                    self.vault_if.execute_vault_operation('KVW', slot_idx, value=value)
                    result = None
                    latency = 5

                else:
                    # fallback: delegar con el nombre de opcode
                    result = self.vault_if.execute_vault_operation(opcode, slot_idx, value=ops.get('rs1_val'))
                    latency = 4

                vault_signal = True
                print(f"  🔧 EX: Bóveda {opcode} slot={slot_idx} result={result}")

            except Exception:
                # propagar excepción para que el pipeline gestione la falla
                raise

        # Operaciones aritméticas básicas
        elif opcode == 'ADD':
            result = UInt64(a_val + b_val)
            print(f"  🔧 EX: ADD {a_val} + {b_val} = {result}")

        elif opcode == 'SUB':
            result = UInt64(a_val - b_val)
            print(f"  🔧 EX: SUB {a_val} - {b_val} = {result}")

        elif opcode == 'AND':
            result = UInt64(a_val & b_val)
            print(f"  🔧 EX: AND {a_val} & {b_val} = {result}")

        elif opcode == 'OR':
            result = UInt64(a_val | b_val)
            print(f"  🔧 EX: OR {a_val} | {b_val} = {result}")

        elif opcode == 'XOR':
            result = UInt64(a_val ^ b_val)
            print(f"  🔧 EX: XOR {a_val} ^ {b_val} = {result}")

        elif opcode == 'ADDI':
            result = UInt64(a_val + imm)
            print(f"  🔧 EX: ADDI {a_val} + {imm} = {result}")

        elif opcode == 'ANDI':
            result = UInt64(a_val & imm)
            print(f"  🔧 EX: ANDI {a_val} & {imm} = {result}")

        # Operaciones de memoria - calcular dirección
        elif opcode in ['LOAD', 'STORE']:
            result = UInt64(a_val + imm)
            print(f"  🔧 EX: {opcode} address = {a_val} + {imm} = {result}")
            latency = 1

        # Operaciones modulares simplificadas
        elif opcode == 'MOD':
            prime = TOYMDMA_CONSTANTS.get('PRIME_MOD', 0xFFFFFFFFFFFFFFFF)
            result = UInt64(a_val % prime)
            print(f"  🔧 EX: MOD {a_val} % {prime} = {result}")
            latency = 2

        elif opcode == 'MULMOD':
            prime = TOYMDMA_CONSTANTS.get('PRIME_MOD', 0xFFFFFFFFFFFFFFFF)
            result = UInt64((a_val * b_val) % prime)
            print(f"  🔧 EX: MULMOD ({a_val} * {b_val}) % {prime} = {result}")
            latency = 3

        # Instrucciones de mezcla/no-lineal delegando en hash_accel
        elif opcode == 'MIXMUL':
            result = mixmul(a_val, b_val)
            latency = 3
            print(f"  🔧 EX: MIXMUL {a_val} *mix* {b_val} = {result}")

        elif opcode == 'MODADD':
            result = modadd(a_val, b_val)
            latency = 3
            print(f"  🔧 EX: MODADD {a_val} + {b_val} mod = {result}")

        elif opcode == 'NONLIN':
            result = nonlin(a_val)
            latency = 4
            print(f"  🔧 EX: NONLIN({a_val}) = {result}")

        # Restauradas: ROTL / ROTR (rotaciones circulares sobre 64 bits)
        elif opcode == 'ROTL':
            # shift tomado de imm (o rs2 si tu convención lo requiere)
            shift = imm % 64
            result = UInt64(a_val).rotl(shift)
            latency = 1
            print(f"  🔧 EX: ROTL {a_val} rol {shift} = {result}")

        elif opcode == 'ROTR':
            shift = imm % 64
            result = UInt64(a_val).rotr(shift)
            latency = 1
            print(f"  🔧 EX: ROTR {a_val} ror {shift} = {result}")

        # --- Nuevas instrucciones: SHIFTL / SHIFTR ---
        elif opcode == 'SHIFTL':
            # Desplazamiento lógico a la izquierda, shift tomado de rs2 o imm
            shift = (b_val if b_val is not None else imm) & 0x3F
            res = ((a_val << shift) & 0xFFFFFFFFFFFFFFFF)
            result = UInt64(res)
            latency = 1
            print(f"  🔧 EX: SHIFTL {a_val} << {shift} = {result}")

        elif opcode == 'SHIFTR':
            # Desplazamiento lógico a la derecha, shift tomado de rs2 o imm
            shift = (b_val if b_val is not None else imm) & 0x3F
            res = (a_val >> shift) & 0xFFFFFFFFFFFFFFFF
            result = UInt64(res)
            latency = 1
            print(f"  🔧 EX: SHIFTR {a_val} >> {shift} = {result}")

        # Mezclas no lineales personalizadas (requieren rf)
        elif opcode == 'CALC_F':
            self._require_rf(opcode)
            A = a_val
            B = b_val
            C = int(self.rf.read("R10"))
            f = (A & B) ^ (A & C)
            result = UInt64(f)
            print(f"  🔧 EX: CALC_F = ({A} & {B}) ^ ({A} & {C}) = {f}")

        elif opcode == 'CALC_G':
            self._require_rf(opcode)
            B = a_val
            C = b_val
            D = int(self.rf.read("R11"))
            g = (B & C) ^ (~B & D)
            result = UInt64(g & 0xFFFFFFFFFFFFFFFF)
            print(f"  🔧 EX: CALC_G = ({B} & {C}) ^ (~{B} & {D}) = {g}")

        elif opcode == 'CALC_H':
            self._require_rf(opcode)
            A = a_val
            B = b_val
            C = int(self.rf.read("R10"))
            D = int(self.rf.read("R11"))
            h = A ^ B ^ C ^ D
            result = UInt64(h)
            print(f"  🔧 EX: CALC_H = {A} ^ {B} ^ {C} ^ {D} = {h}")

        # UPDATE_* (requieren rf)
        elif opcode in ('UPDATE_A', 'UPDATE_B', 'UPDATE_C', 'UPDATE_D'):
            self._require_rf(opcode)
            funct_val = ops.get('funct', 0)
            rs3_idx = (funct_val >> 5) & 0b11111
            rs4_idx = funct_val & 0b11111
            rs3_val = int(self.rf.read(f"R{rs3_idx}"))
            rs4_val = int(self.rf.read(f"R{rs4_idx}"))

            if opcode == 'UPDATE_A':
                A = a_val
                f = b_val
                mul = rs3_val
                B = rs4_val
                temp = (A + f + mul) & 0xFFFFFFFFFFFFFFFF
                rot = ((temp << 7) | (temp >> (64 - 7))) & 0xFFFFFFFFFFFFFFFF
                result = UInt64((rot + B) & 0xFFFFFFFFFFFFFFFF)
                print(f"  🔧 EX: UPDATE_A = rol64({A} + {f} + {mul}, 7) + {B} = {result}")

            elif opcode == 'UPDATE_B':
                Bv = a_val
                g = b_val
                block = rs3_val
                C = rs4_val
                temp = (Bv + g + block) & 0xFFFFFFFFFFFFFFFF
                rot = ((temp << 11) | (temp >> (64 - 11))) & 0xFFFFFFFFFFFFFFFF
                result = UInt64((rot + (C * 3)) & 0xFFFFFFFFFFFFFFFF)
                print(f"  🔧 EX: UPDATE_B = rol64({Bv} + {g} + {block}, 11) + ({C} * 3) = {result}")

            elif opcode == 'UPDATE_C':
                C = a_val
                h = b_val
                mul = rs3_val
                D = rs4_val
                prime = TOYMDMA_CONSTANTS.get('PRIME_MOD', 0xFFFFFFFFFFFFFFFF)
                temp = (C + h + mul) & 0xFFFFFFFFFFFFFFFF
                rot = ((temp << 17) | (temp >> (64 - 17))) & 0xFFFFFFFFFFFFFFFF
                result = UInt64((rot + (D % prime)) & 0xFFFFFFFFFFFFFFFF)
                print(f"  🔧 EX: UPDATE_C = rol64({C} + {h} + {mul}, 17) + ({D} % {prime}) = {result}")

            elif opcode == 'UPDATE_D':
                Dv = a_val
                A = b_val
                block = rs3_val
                f = rs4_val
                temp = (Dv + A + block) & 0xFFFFFFFFFFFFFFFF
                rot = ((temp << 19) | (temp >> (64 - 19))) & 0xFFFFFFFFFFFFFFFF
                result = UInt64((rot ^ (f * 5)) & 0xFFFFFFFFFFFFFFFF)
                print(f"  🔧 EX: UPDATE_D = rol64({Dv} + {A} + {block}, 19) ^ ({f} * 5) = {result}")

        else:
            # Instrucción no implementada en EX (puede ser control/unknown)
            pass

        # Actualizar métricas
        self.metrics['exec_count'] += 1
        self.metrics['cycles'] += latency
        self.metrics['op_latency'][opcode] = latency

        return {
            'result': result,
            'latency': latency,
            'vault_signal': vault_signal
        }

    def get_metrics(self):
        return dict(self.metrics)