# execute_stage.py

"""
Etapa EX (Execute) del pipeline.
Responsabilidad:
 - Ejecutar operaciones aritméticas, lógicas, modulares, no lineales, y señales de bóveda.
 - Recibir operandos y señales de control desde la etapa ID.
 - Retornar resultado para MEM/WB y métricas de ejecución.
"""
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'isa')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'vault')))
from vault_interface import VaultInterface
from isa_types import UInt64, Vec4x64
from hash_accel import mixmul, modadd, nonlin
from isa_definition import TOYMDMA_CONSTANTS

class ExecuteStage:
    def __init__(self, vault_if: VaultInterface | None = None):
        self.metrics = {
            'exec_count': 0,
            'cycles': 0,
            'op_latency': {},
        }
        # Interfaz a la bóveda (puede ser None en tests unitarios simples)
        self.vault_if = vault_if

    def execute(self, decoded_instr):
        """
        Ejecuta la operación indicada por la instrucción decodificada - CORREGIDO
        """
        opcode = decoded_instr['opcode_name']
        ops = decoded_instr['operandos']
        ctrl = decoded_instr['control_signals']
        result = None
        latency = 1

        # DEBUG: Mostrar qué operandos tenemos
        print(f"  🔧 EX: Operandos disponibles: {list(ops.keys())}")
        
        # Extraer operandos CORRECTAMENTE
        rs1_val = ops.get('rs1_val', UInt64(0))
        rs2_val = ops.get('rs2_val', UInt64(0))
        imm_val = ops.get('imm', 0)
        
        # Convertir a enteros para operaciones
        a_val = int(rs1_val) if hasattr(rs1_val, 'value') else int(rs1_val)
        b_val = int(rs2_val) if hasattr(rs2_val, 'value') else int(rs2_val)
        imm = int(imm_val) if hasattr(imm_val, 'value') else int(imm_val)
        
        print(f"  🔧 EX: a_val={a_val}, b_val={b_val}, imm={imm}")

       # Si la instrucción requiere acceso a la bóveda, delegar
        vault_signal = None
        if ctrl.get('use_boveda', False):
            if not self.vault_if:
                raise RuntimeError("VaultInterface no configurada en ExecuteStage para instrucción de bóveda")

            slot_idx = ops.get('vault_idx')
            # Normalizar nombres: aceptar tanto VSTORE/KVW como KVL/VLOAD/SGEN...
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
                    # operación específica sobre slot (parámetros libres según diseño)
                    result = self.vault_if.execute_vault_operation('KVOP', slot_idx, op=ops.get('funct'), value=ops.get('rs1_val'))
                    latency = 6

                elif opcode in ('SGEN', 'SIGN'):
                    # generar firma: se espera `hash_state` o un Vec4x64 en ops
                    state = ops.get('hash_state') or ops.get('rs1_val')
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

            except Exception as e:
                # propagar excepción para que el pipeline gestione la falla
                raise
        
        # Operaciones aritméticas básicas - CORREGIDAS
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
            # CORRECCIÓN: Sumar registro + inmediato
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
        
        # Operaciones de rotación
        elif opcode == 'ROTL':
            shift = imm % 64
            result = UInt64((a_val << shift) | (a_val >> (64 - shift)))
            print(f"  🔧 EX: ROTL {a_val} << {shift} = {result}")
            
        elif opcode == 'ROTR':
            shift = imm % 64
            result = UInt64((a_val >> shift) | (a_val << (64 - shift)))
            print(f"  🔧 EX: ROTR {a_val} >> {shift} = {result}")

        
        # Mezclas no lineales personalizadas
        elif opcode == 'CALC_F':
            # f = (A & B) ^ (A & C)
            A = a_val
            B = b_val
            C = self.rf.read("R10") # R10 = C
            f = (A & B) ^ (A & C)
            result = UInt64(f)
            print(f"  🔧 EX: CALC_F = ({A} & {B}) ^ ({A} & {C}) = {f}")

        elif opcode == 'CALC_G':
            # g = (B & C) ^ (~B & D)
            B = a_val
            C = b_val
            D = self.rf.read("R11")  # R11 = D
            g = (B & C) ^ (~B & D)
            result = UInt64(g)
            print(f"  🔧 EX: CALC_G = ({B} & {C}) ^ (~{B} & {D}) = {g}")

        elif opcode == 'CALC_H':
            # h = A ^ B ^ C ^ D
            A = a_val
            B = b_val
            C = self.rf.read("R10")  # R10 = C
            D = self.rf.read("R11")  # R11 = D
            h = A ^ B ^ C ^ D
            result = UInt64(h)
            print(f"  🔧 EX: CALC_H = {A} ^ {B} ^ {C} ^ {D} = {h}")


        elif opcode == 'UPDATE_A':
            # Extraer rs3 y rs4 desde funct
            funct_val = ops.get('funct', 0)
            rs3_idx = (funct_val >> 5) & 0b11111
            rs4_idx = funct_val & 0b11111
            rs3_val = self.rf.read(f"R{rs3_idx}")
            rs4_val = self.rf.read(f"R{rs4_idx}")

            A = a_val
            f = b_val
            mul = int(rs3_val)
            B = int(rs4_val)

            temp = (A + f + mul) & 0xFFFFFFFFFFFFFFFF
            rot = ((temp << 7) | (temp >> (64 - 7))) & 0xFFFFFFFFFFFFFFFF
            result = UInt64(rot + B)
            print(f"  🔧 EX: UPDATE_A = rol64({A} + {f} + {mul}, 7) + {B} = {result}")

        elif opcode == 'UPDATE_B':
            funct_val = ops.get('funct', 0)
            rs3_idx = (funct_val >> 5) & 0b11111
            rs4_idx = funct_val & 0b11111
            rs3_val = self.rf.read(f"R{rs3_idx}")
            rs4_val = self.rf.read(f"R{rs4_idx}")

            B = a_val
            g = b_val
            block = int(rs3_val)
            C = int(rs4_val)

            temp = (B + g + block) & 0xFFFFFFFFFFFFFFFF
            rot = ((temp << 11) | (temp >> (64 - 11))) & 0xFFFFFFFFFFFFFFFF
            result = UInt64(rot + (C * 3))
            print(f"  🔧 EX: UPDATE_B = rol64({B} + {g} + {block}, 11) + ({C} * 3) = {result}")

        elif opcode == 'UPDATE_C':
            funct_val = ops.get('funct', 0)
            rs3_idx = (funct_val >> 5) & 0b11111
            rs4_idx = funct_val & 0b11111
            rs3_val = self.rf.read(f"R{rs3_idx}")
            rs4_val = self.rf.read(f"R{rs4_idx}")

            C = a_val
            h = b_val
            mul = int(rs3_val)
            D = int(rs4_val)
            prime = TOYMDMA_CONSTANTS.get('PRIME_MOD', 0xFFFFFFFFFFFFFFFF)

            temp = (C + h + mul) & 0xFFFFFFFFFFFFFFFF
            rot = ((temp << 17) | (temp >> (64 - 17))) & 0xFFFFFFFFFFFFFFFF
            result = UInt64(rot + (D % prime))
            print(f"  🔧 EX: UPDATE_C = rol64({C} + {h} + {mul}, 17) + ({D} % {prime}) = {result}")

        elif opcode == 'UPDATE_D':
            funct_val = ops.get('funct', 0)
            rs3_idx = (funct_val >> 5) & 0b11111
            rs4_idx = funct_val & 0b11111
            rs3_val = self.rf.read(f"R{rs3_idx}")
            rs4_val = self.rf.read(f"R{rs4_idx}")

            D = a_val
            A = b_val
            block = int(rs3_val)
            f = int(rs4_val)

            temp = (D + A + block) & 0xFFFFFFFFFFFFFFFF
            rot = ((temp << 19) | (temp >> (64 - 19))) & 0xFFFFFFFFFFFFFFFF
            result = UInt64(rot ^ (f * 5))
            print(f"  🔧 EX: UPDATE_D = rol64({D} + {A} + {block}, 19) ^ ({f} * 5) = {result}")


        
        else:
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