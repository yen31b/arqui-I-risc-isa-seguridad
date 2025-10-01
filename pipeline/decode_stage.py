# decode_stage.py

"""
Etapa ID (Instruction Decode) del pipeline.
Responsabilidad:
 - Decodificar la instrucción binaria.
 - Identificar tipo de operación (hash, bóveda, firma, aritmética).
 - Extraer operandos (registros, inmediatos).
 - Generar señales de control para la etapa EX.
"""
import sys
import os
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', 'isa')))

from isa_definition import (
    get_field_value,
    INST_FORMATS,
    OPCODES,
    FUNCT_CODES,
    INSTRUCTION_ADDRESSING_MODES,
    ADDRESSING_MODE_FORMAT_MAP
)
from addressing_modes import (
    mode_REG,
    mode_REG_IMM,
    mode_BASE_DISP,
    mode_IMM_LONG
)
from register_file import register_file


class DecodeStage:
    def __init__(self, register_file: register_file):
        self.rf = register_file
        self.metrics = {'decode_count': 0, 'cycles': 0}

    def decode(self, instruction):
        """
        Decodifica una instrucción binaria y genera señales de control.
        Retorna un diccionario con:
         - opcode_name
         - format_type
         - operandos
         - control_signals
        """
        result = {}
        opcode = get_field_value(instruction, 'opcode', 'R_TYPE')

        # Buscar nombre del opcode
        opcode_name = next(
            (name for name, code in OPCODES.items() if code == opcode), 'UNKNOWN')
        result['opcode_name'] = opcode_name

        # Determinar formato de instrucción
        format_type = next((fmt for fmt, info in INST_FORMATS.items()
                            if 'opcode' in info['fields'] and get_field_value(instruction, 'opcode', fmt) == opcode),
                           'R_TYPE')
        result['format_type'] = format_type

        # Extraer operandos según formato
        fields = INST_FORMATS[format_type]['fields']
        operandos = {}
        for field in fields:
            operandos[field] = get_field_value(instruction, field, format_type)
        result['operandos'] = operandos

        # Generar señales de control
        control_signals = {
            'use_boveda': opcode_name in ['VINIT', 'KVOP', 'KVL', 'SIGN'],
            'is_hash': opcode_name in ['HASH_INIT', 'HASH_BLOCK', 'HASH_FINAL'],
            'is_arithmetic': opcode_name in ['ADD', 'SUB', 'AND', 'OR', 'XOR', 'ADDI', 'ANDI'],
            'is_modular': opcode_name in ['MOD', 'MODADD', 'MULMOD'],
            'is_nonlin': opcode_name in ['NONLIN', 'ROTL', 'ROTR'],
            'needs_imm': 'imm' in fields,
            'addressing_mode': INSTRUCTION_ADDRESSING_MODES.get(opcode_name, None)
        }
        result['control_signals'] = control_signals

        self.metrics['decode_count'] += 1
        self.metrics['cycles'] += 1

        return result

    def get_metrics(self):
        return dict(self.metrics)
