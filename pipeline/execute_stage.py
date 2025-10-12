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

from isa_types import UInt64, Vec4x64
from hash_accel import mixmul, modadd, nonlin
from isa_definition import TOYMDMA_CONSTANTS

class ExecuteStage:
    def __init__(self):
        self.metrics = {
            'exec_count': 0,
            'cycles': 0,
            'op_latency': {},
        }

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

        # Ejecutar operación
        vault_signal = None
        
        # Operaciones aritméticas básicas - CORREGIDAS
        if opcode == 'ADD':
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

        
        else:
            # Para instrucciones no implementadas
            result = UInt64(0)
            print(f"  ⚠️  EX: Opcode {opcode} no implementado, retornando 0")

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