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
from isa.hash_accel import mixmul, modadd, nonlin, apply_block  # añadido apply_block
from isa.isa_definition import TOYMDMA_CONSTANTS

class ExecuteStage:
    def __init__(self, vault_if: VaultInterface | None = None, rf = None):
        self.metrics = {
            'exec_count': 0,
            'cycles': 0,
            'op_latency': {},
            # contadores adicionales para control de flujo
            'jumps': 0,
            'branches': 0,
        }
        # Interfaz a la bóveda (puede ser None en tests unitarios simples)
        self.vault_if = vault_if
        # Referencia opcional al banco de registros (permitir lecturas desde EX)
        self.rf = rf

    def get_metrics(self):
        """
        Retorna métricas de ejecución. Normaliza op_latency para que cada opcode
        tenga un valor escalar (última latencia observada), como esperan los tests.
        """
        out = dict(self.metrics)
        op_lat = out.get('op_latency', {})
        if isinstance(op_lat, dict):
            normalized = {}
            for op, vals in op_lat.items():
                if isinstance(vals, list) and vals:
                    normalized[op] = vals[-1]
                else:
                    normalized[op] = vals
            out['op_latency'] = normalized
        return out

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

        # Obtener PC actual (fetch ya incrementó PC); usar 0 si no hay rf
        if self.rf is not None:
            try:
                pc_val = int(self.rf.read('PC'))
            except Exception:
                pc_val = 0
        else:
            pc_val = 0

        # Helper: sign-extend 16-bit immediate a entero con signo (offset en bytes)
        def sign_extend_16(x):
            x = int(x) & 0xFFFF
            if x & 0x8000:
                return x - (1 << 16)
            return x

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

                elif opcode == 'VERIFY':
                    # Construir estado (hash) como Vec4x64
                    state = ops.get('hash_state')
                    if state is None:
                        # intentar R4..R7
                        try:
                            s_vec = Vec4x64([self.rf.read('R4'), self.rf.read('R5'), self.rf.read('R6'), self.rf.read('R7')])
                        except Exception:
                            s_vec = None
                        # si parece cero y hay rs1 (base de firma), deducir state_base = rs1 - 4
                        def _is_zero_vec(v):
                            try:
                                return all(int(v[i]) == 0 for i in range(4))
                            except Exception:
                                return False
                        if (s_vec is None or _is_zero_vec(s_vec)) and ('rs1' in ops and ops['rs1'] is not None):
                            try:
                                base = max(int(ops['rs1']) - 4, 0)
                                s_alt = Vec4x64([self.rf.read(f"R{base + i}") for i in range(4)])
                                state = s_alt
                                print(f"  🔧 EX: VERIFY(using vault) state R{base}..R{base+3} = {state}")
                            except Exception:
                                state = s_vec
                        else:
                            state = s_vec
                    # Construir firma (signature) como Vec4x64
                    sig = ops.get('signature')
                    if sig is None and 'rs1' in ops and ops['rs1'] is not None:
                        try:
                            base_sig = int(ops['rs1'])
                            sig = Vec4x64([self.rf.read(f"R{base_sig + i}") for i in range(4)])
                            print(f"  🔧 EX: VERIFY(using vault) signature R{base_sig}..R{base_sig+3} = {sig}")
                        except Exception:
                            sig = None
                    verified = False
                    try:
                        verified = bool(self.vault_if.execute_vault_operation('VERIFY', slot_idx, state=state, signature=sig))
                    except Exception:
                        verified = False
                    result = UInt64(1 if verified else 0)
                    latency = 6

                else:
                    # fallback: delegar con el nombre de opcode
                    result = self.vault_if.execute_vault_operation(opcode, slot_idx, value=ops.get('rs1_val'))
                    latency = 4

                vault_signal = True
                print(f"  🔧 EX: Bóveda {opcode} slot={slot_idx} result={result}")

            except Exception as e:
                # Manejar errores de bóveda sin abortar el pipeline
                try:
                    # import local para evitar dependencias circulares en top-level
                    from vault.vault import VaultAccessError
                except Exception:
                    VaultAccessError = Exception  # fallback genérico

                # Registrar y mostrar traza clara
                print(f"  ⚠️  EX: Error de bóveda en {opcode} slot={slot_idx}: {e}")
                # Incrementar contador de violaciones local en métricas de EX
                self.metrics['vault_violations'] = self.metrics.get('vault_violations', 0) + 1
                # Indicar que la EX intentó la operación (para que MEM no la re-ejecute)
                vault_signal = True
                # No propagar la excepción: devolver resultado nulo para continuar ejecución
                result = None
                # latencia mínima para la operación fallida (para contabilizar coste)
                latency = max(latency, 1)

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

        elif opcode == 'LOADI':
            # La instrucción LOADI ignora rs1 y toma sólo el inmediato
            result = UInt64(imm)
            print(f"  🔧 EX: LOADI  imm = {imm} → {result}")
            return {'result': result, 'latency': 1}

        elif opcode == 'ANDI':
            result = UInt64(a_val & imm)
            print(f"  🔧 EX: ANDI {a_val} & {imm} = {result}")

        # Operaciones de memoria - calcular dirección
        elif opcode in ['LOAD', 'STORE']:
            result = UInt64(a_val + imm)
            print(f"  🔧 EX: {opcode} address = {a_val} + {imm} = {result}")
            latency = 1

        ####################################
        # Control de flujo: JUMP / BEQ / BNE
        elif opcode == 'JUMP':
            # imm se interpreta como offset (signed 16-bit) en bytes relativo al PC actual (que ya apunta a next instruction)
            offset = sign_extend_16(imm)
            target = UInt64(pc_val + offset)
            self.metrics['jumps'] = self.metrics.get('jumps', 0) + 1
            print(f"  🔧 EX: JUMP   PC({hex(pc_val)}) + {offset} = {hex(int(target))}")
            return {
                'result': None,
                'latency': 1,
                'branch_taken': True,
                'target_pc': target
            }

        elif opcode == 'BEQ':
            offset = sign_extend_16(imm)
            taken = (a_val == b_val)
            self.metrics['branches'] = self.metrics.get('branches', 0) + 1
            print(f"  🔧 EX: BEQ    {a_val} == {b_val}? {'taken' if taken else 'not taken'}")
            return {
                'result': None,
                'latency': 1,
                'branch_taken': taken,
                'target_pc': UInt64(pc_val + offset) if taken else None
            }

        elif opcode == 'BNE':
            offset = sign_extend_16(imm)
            taken = (a_val != b_val)
            self.metrics['branches'] = self.metrics.get('branches', 0) + 1
            print(f"  🔧 EX: BNE    {a_val} != {b_val}? {'taken' if taken else 'not taken'}")
            return {
                'result': None,
                'latency': 1,
                'branch_taken': taken,
                'target_pc': UInt64(pc_val + offset) if taken else None
            }
    

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

        # { added: MUL - multiplicación truncada a 64 bits }
        elif opcode == 'MUL':
            # Multiplicación truncada a 64 bits (comportamiento común en ISAs R-type)
            res = (a_val * b_val) & 0xFFFFFFFFFFFFFFFF
            result = UInt64(res)
            latency = 3
            print(f"  🔧 EX: MUL {a_val} * {b_val} -> {result}")

        # --- Añadidas: HASH_INIT y HASH_BLOCK ---
        elif opcode == 'HASH_INIT':
            # Intentar leer IVs HASH_A..HASH_D desde la bóveda (índices 4..7).
            vals = None
            if self.vault_if:
                try:
                    vals_tmp = []
                    for idx in range(4, 8):
                        handle = self.vault_if.execute_vault_operation('KVL', idx)
                        # handle puede ser KeyHandle; usar xor_scalar(0) para recuperar valor
                        if hasattr(handle, 'xor_scalar'):
                            v = handle.xor_scalar(0)
                            vals_tmp.append(int(v))
                        else:
                            # si la interfaz devolviera directamente un entero
                            vals_tmp.append(int(handle))
                    vals = vals_tmp
                    print(f"  🔧 EX: HASH_INIT leídos desde bóveda: {vals}")
                except Exception:
                    vals = None

            if vals is None:
                vals = [
                    TOYMDMA_CONSTANTS.get('INITIAL_A'),
                    TOYMDMA_CONSTANTS.get('INITIAL_B'),
                    TOYMDMA_CONSTANTS.get('INITIAL_C'),
                    TOYMDMA_CONSTANTS.get('INITIAL_D'),
                ]
                print(f"  🔧 EX: HASH_INIT usando constantes: {vals}")

            # Escribir en R4..R7 si hay register file
            if self.rf:
                self.rf.write('R4', UInt64(vals[0]))
                self.rf.write('R5', UInt64(vals[1]))
                self.rf.write('R6', UInt64(vals[2]))
                self.rf.write('R7', UInt64(vals[3]))
            result = Vec4x64(vals)
            latency = 4

        elif opcode == 'HASH_BLOCK':
            # Procesar bloque de 64 bits provisto en rs1 (a_val)
            block = a_val
            self._require_rf(opcode)
            # leer estado actual de R4..R7
            current_state = Vec4x64([self.rf.read('R4'), self.rf.read('R5'), self.rf.read('R6'), self.rf.read('R7')])
            # aplicar función de bloque
            try:
                new_state = apply_block(current_state, block)
            except Exception as e:
                raise

            # escribir nuevo estado en R4..R7
            self.rf.write('R4', int(new_state[0]))
            self.rf.write('R5', int(new_state[1]))
            self.rf.write('R6', int(new_state[2]))
            self.rf.write('R7', int(new_state[3]))
            result = new_state
            latency = 6
            print(f"  🔧 EX: HASH_BLOCK procesado, nuevo estado R4..R7 = {new_state}")

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
            # Usa el registro rs2 (b_val) o inmediato si no hay
            shift = (b_val if b_val is not None else imm) & 0x3F
            result = UInt64(a_val).rotl(shift)
            latency = 1
            print(f"  🔧 EX: ROTL {a_val} rol {shift} = {result}")

        elif opcode == 'ROTR':
            shift = (b_val if b_val is not None else imm) & 0x3F
            result = UInt64(a_val).rotr(shift)
            latency = 1
            print(f"  🔧 EX: ROTR {a_val} ror {shift} = {result}")


        # --- Nuevas instrucciones: SHIFTL / SHIFTR ---
        elif opcode == 'SHIFTL':
            # Desplazamiento lógico a la izquierda, shift tomado de rs2 o imm
            shift = (b_val if b_val is not None else imm) & 0x3F
            res = ((a_val << shift) & 0xFFFFFFFFFFFFFFFF)
            result = UInt64(res)
            latency = 2
            print(f"  🔧 EX: SHIFTL {a_val} * {b_val} -> {result}")

        elif opcode == 'SHIFTR':
            # Desplazamiento lógico a la derecha, shift tomado de rs2 o imm
            shift = (b_val if b_val is not None else imm) & 0x3F
            res = (a_val >> shift) & 0xFFFFFFFFFFFFFFFF
            result = UInt64(res)
            latency = 1
            print(f"  🔧 EX: SHIFTR {a_val} >> {shift} = {result}")

        # --- Nuevas: UPDATE_A/B/C/D (usando funct = (rs3<<5) | rs4) ---
        elif opcode in ('UPDATE_A', 'UPDATE_B', 'UPDATE_C', 'UPDATE_D'):
            self._require_rf(opcode)
            MASK64 = 0xFFFFFFFFFFFFFFFF
            # funct codifica dos registros: rs3 y rs4 (5 bits cada uno)
            rs3rs4 = int(ops.get('funct', 0))
            rs3_idx = (rs3rs4 >> 5) & 0x1F
            rs4_idx = rs3rs4 & 0x1F
            v3 = int(self.rf.read(f"R{rs3_idx}"))
            v4 = int(self.rf.read(f"R{rs4_idx}"))
            # temp = rs1_val + rs2_val + rs3
            temp = (a_val + b_val + v3) & MASK64
            # rotación según la instrucción
            rot_map = {
                'UPDATE_A': 7,
                'UPDATE_B': 11,
                'UPDATE_C': 17,
                'UPDATE_D': 19,
            }
            r = rot_map[opcode]
            rot = ((temp << r) | (temp >> (64 - r))) & MASK64
            if opcode == 'UPDATE_A':
                res = (rot + v4) & MASK64
            elif opcode == 'UPDATE_B':
                res = (rot + (v4 * 3)) & MASK64
            elif opcode == 'UPDATE_C':
                prime = TOYMDMA_CONSTANTS.get('PRIME_MOD', 0xFFFFFFFFFFFFFFFF)
                res = (rot + (v4 % int(prime))) & MASK64
            else:  # UPDATE_D
                res = (rot ^ (v4 * 5)) & MASK64
            result = UInt64(res)
            latency = 3
            print(f"  🔧 EX: {opcode} -> {result} (rs3=R{rs3_idx}, rs4=R{rs4_idx})")
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

        # HASH_FINAL rd: exportar estado hash (Vec4x64). rd puede venir en 'rs1' o 'rd' según encoding.
        elif opcode == 'HASH_FINAL':
            self._require_rf(opcode)
            state = Vec4x64([self.rf.read('R4'), self.rf.read('R5'), self.rf.read('R6'), self.rf.read('R7')])
            # intentar escribir en registro destino si se indica (rs1 como base)
            dest = None
            if 'rd' in ops:
                dest = ops.get('rd')
            elif 'rs1' in ops:
                dest = ops.get('rs1')
            if dest is not None and self.rf:
                base = int(dest)
                # escribir state en registros contiguos R{base}..R{base+3} si hay espacio
                for i in range(4):
                    regname = f"R{base + i}"
                    self.rf.write(regname, int(state[i]))
                print(f"  🔧 EX: HASH_FINAL -> escritos R{base}..R{base+3}")
            result = state
            latency = 4

        # VERIFY rd, vault_idx, firma : verificar firma contra llave en bóveda (devuelve flag en rd)
        elif opcode == 'VERIFY':
            if not self.vault_if:
                raise RuntimeError("VaultInterface no configurada para VERIFY")
            # slot index puede venir como vault_idx o en funct
            slot_idx = ops.get('vault_idx', ops.get('funct'))
            # 1) Construir estado (hash) como Vec4x64
            state = ops.get('hash_state')
            if state is None:
                # a) Fallback a R4..R7
                try:
                    s_vec = Vec4x64([self.rf.read('R4'), self.rf.read('R5'), self.rf.read('R6'), self.rf.read('R7')])
                except Exception:
                    s_vec = None
                # b) Si R4..R7 parecen nulos y tenemos rs1 (base de firma), deducir state_base = rs1 - 4 (patrón SGEN→VERIFY)
                def _is_zero_vec(v):
                    try:
                        return all(int(v[i]) == 0 for i in range(4))
                    except Exception:
                        return False
                if (s_vec is None or _is_zero_vec(s_vec)) and ('rs1' in ops and ops['rs1'] is not None):
                    try:
                        base = max(int(ops['rs1']) - 4, 0)
                        s_alt = Vec4x64([self.rf.read(f"R{base + i}") for i in range(4)])
                        state = s_alt
                        print(f"  🔧 EX: VERIFY usando state deducido R{base}..R{base+3} = {state}")
                    except Exception:
                        state = s_vec
                else:
                    state = s_vec
            # 2) Construir firma (signature) como Vec4x64
            sig = ops.get('signature')
            if sig is None:
                # si no vino precompuesta, intentamos desde rs1 base
                if 'rs1' in ops and ops['rs1'] is not None:
                    try:
                        base_sig = int(ops['rs1'])
                        sig = Vec4x64([self.rf.read(f"R{base_sig + i}") for i in range(4)])
                        print(f"  🔧 EX: VERIFY leyendo signature R{base_sig}..R{base_sig+3} = {sig}")
                    except Exception:
                        sig = None
                # último recurso: repetir componente (menos ideal, pero evita excepciones)
                if sig is None and 'rs1_val' in ops:
                    v = int(ops['rs1_val'])
                    sig = Vec4x64([v, v, v, v])
                    print("  🔧 EX: VERIFY signature desde rs1_val (repetido)")

            # delegar verificación a la interfaz de bóveda
            verified = False
            try:
                verified = bool(self.vault_if.execute_vault_operation('VERIFY', slot_idx, state=state, signature=sig))
            except Exception as e:
                verified = False
            result = UInt64(1 if verified else 0)
            latency = 6
            print(f"  🔧 EX: VERIFY slot={slot_idx} -> {'OK' if verified else 'FAIL'}")

        # Actualizar métricas
        self.metrics['exec_count'] += 1
        self.metrics['op_latency'].setdefault(opcode, []).append(latency)
        self.metrics['cycles'] += latency

        return {
            'result': result,
            'latency': latency,
            'vault_signal': vault_signal
        }