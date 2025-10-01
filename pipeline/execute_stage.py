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
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', 'isa')))

from isa_types import UInt64, Vec4x64
from hash_accel import mixmul, modadd, nonlin
#from vault import generate_vault_signal

class ExecuteStage:
    def __init__(self):
        self.metrics = {
            'exec_count': 0,
            'cycles': 0,
            'op_latency': {},  # e.g. {'ADD': 1, 'MULMOD': 3}
        }

    def execute(self, decoded_instr):
        """
        Ejecuta la operación indicada por la instrucción decodificada.
        Entrada:
         - decoded_instr: dict con 'opcode_name', 'operandos', 'control_signals'
        Salida:
         - dict con 'result', 'latency', 'vault_signal' (si aplica)
        """
        opcode = decoded_instr['opcode_name']
        ops = decoded_instr['operandos']
        ctrl = decoded_instr['control_signals']
        result = None
        latency = 1  # Por defecto

        # Extraer operandos
        a = UInt64(ops.get('rs1_val', 0))
        b = UInt64(ops.get('rs2_val', 0))
        imm = UInt64(ops.get('imm', 0))

        # Ejecutar operación
        if ctrl['is_arithmetic']:
            if opcode == 'ADD':
                result = a + b
            elif opcode == 'SUB':
                result = a - b
            elif opcode == 'AND':
                result = a & b
            elif opcode == 'OR':
                result = a | b
            elif opcode == 'XOR':
                result = a ^ b
            elif opcode == 'ADDI':
                result = a + imm
            elif opcode == 'ANDI':
                result = a & imm

        elif ctrl['is_modular']:
            if opcode == 'MOD':
                result = mod(a)
                latency = 2
            elif opcode == 'MODADD':
                result = modadd(a, b)
                latency = 2
            elif opcode == 'MULMOD':
                result = mulmod(a, b)
                latency = 3

        elif ctrl['is_nonlin']:
            if opcode == 'NONLIN':
                result = nonlin(a)
                latency = 2
            elif opcode == 'ROTL':
                result = a.rotl(imm)
            elif opcode == 'ROTR':
                result = a.rotr(imm)

        elif ctrl['use_boveda']:
            result = None  # No produce resultado directo
            vault_signal = generate_vault_signal(opcode, ops)
        else:
            result = None  # Instrucción desconocida o no ejecutable

        # Actualizar métricas
        self.metrics['exec_count'] += 1
        self.metrics['cycles'] += latency
        self.metrics['op_latency'].setdefault(opcode, latency)

        return {
            'result': result,
            'latency': latency,
            'vault_signal': vault_signal if ctrl['use_boveda'] else None
        }

    def get_metrics(self):
        return dict(self.metrics)
