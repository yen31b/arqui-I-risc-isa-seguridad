# decode_stage.py - VERSIÓN SIMPLIFICADA Y ROBUSTA

"""
Etapa ID (Instruction Decode) del pipeline.
"""
from isa.isa_definition import (
    get_field_value,
    INST_FORMATS,
    OPCODES,
    INSTRUCTION_ADDRESSING_MODES,
    VAULT_INSTR_NAMES
)
from isa.register_file import register_file


class DecodeStage:
    def __init__(self, register_file: register_file):
        self.rf = register_file
        self.metrics = {'decode_count': 0, 'cycles': 0}

    def decode(self, instruction):
        """
        Decodifica una instrucción binaria - VERSIÓN SIMPLIFICADA
        """
        result = {}
        
        # ESTRATEGIA SIMPLE: Determinar formato por OPCODE manualmente
        # Extraer opcode como R_TYPE primero (bits 31-26 siempre son opcode)
        opcode_bits = (instruction >> 26) & 0x3F
        
        # Buscar nombre del opcode
        opcode_name = next((name for name, code in OPCODES.items() if code == opcode_bits), 'UNKNOWN')
        result['opcode_name'] = opcode_name
        
        # Mapear opcode a formato
        format_type = self._map_opcode_to_format(opcode_name)
        result['format_type'] = format_type

        print(f"  🔍 DECODE: Opcode {opcode_name} (0x{opcode_bits:x}) → Formato {format_type}")

        # Extraer operandos según el formato
        fields = INST_FORMATS[format_type]['fields']
        operandos = {}
        
        for field in fields:
            try:
                value = get_field_value(instruction, field, format_type)
                # Si el campo es inmediato, decidir si hacer sign-extend o zero-extend
                if field == 'imm':
                    # Opcodes donde el inmediato se interpreta como signed offset / signed immediate
                    SIGNED_IMM_OPCODES = {
                        'ADDI', 'LOAD', 'STORE', 'BEQ', 'BNE', 'JUMP', 'BLT'
                    }
                    if opcode_name in SIGNED_IMM_OPCODES:
                        start, end = INST_FORMATS[format_type]['fields'][field]
                        width = start - end + 1
                        # sign-extend width->python int (signed)
                        if value & (1 << (width - 1)):
                            value = value - (1 << width)
                    else:
                        # zero-extend: keep raw unsigned 0..(2^width-1)
                        pass

                operandos[field] = value
                # Mostrar inmediato en hex si proviene de campo imm y es negativo
                if field == 'imm' and isinstance(value, int) and value < 0:
                    print(f"  🔍 DECODE: {field} = {value} (signed) (0x{(value & ((1<<64)-1)):x})")
                else:
                    print(f"  🔍 DECODE: {field} = {value} (0x{value:x})")
            except Exception as e:
                print(f"  ⚠️  DECODE: Error extrayendo {field}: {e}")
                operandos[field] = 0
        
        result['operandos'] = operandos

        # Si la instrucción de firma lleva destino codificado en 'funct',
        # normalizar a 'rd' y, cuando corresponda (p.ej. H_TYPE), exponer también vault_idx
        if opcode_name in ('SGEN', 'SIGN', 'VERIFY'):
            funct_val = operandos.get('funct')
            if funct_val is not None:
                try:
                    f = int(funct_val)
                    rd_candidate = f & 0x1F
                    operandos['rd'] = rd_candidate
                    # Si el formato es H_TYPE (o no existe vault_idx), extraer slot desde los bits altos de funct
                    if (format_type == 'H_TYPE') and ('vault_idx' not in operandos or operandos.get('vault_idx') in (0, None)):
                        slot_candidate = (f >> 5)
                        operandos['vault_idx'] = slot_candidate
                except Exception:
                    pass
                

        # Generar señales de control
        control_signals = {
            # 'use_boveda' ahora viene desde la definición centralizada
            'use_boveda': opcode_name in VAULT_INSTR_NAMES,
            'is_hash': opcode_name in ['HASH_INIT', 'HASH_BLOCK', 'HASH_FINAL'],
            'is_arithmetic': opcode_name in ['ADD', 'SUB', 'AND', 'OR', 'XOR', 'ADDI', 'ANDI'],
            'is_modular': opcode_name in ['MOD', 'MODADD', 'MULMOD'],
            'is_nonlin': opcode_name in ['NONLIN', 'ROTL', 'ROTR'],
            'is_shift': opcode_name in ['SHIFTL', 'SHIFTR'],
            'needs_imm': format_type in ['I_TYPE', 'S_TYPE'],
            'addressing_mode': INSTRUCTION_ADDRESSING_MODES.get(opcode_name, None)
        }
        result['control_signals'] = control_signals

        self.metrics['decode_count'] += 1
        self.metrics['cycles'] += 1

        return result

    def _map_opcode_to_format(self, opcode_name):
        """
        Mapea simple de opcode a formato
        """
        format_map = {
             # I_TYPE
             'ADDI': 'I_TYPE', 'ANDI': 'I_TYPE', 'LOAD': 'I_TYPE', 'LOADI': 'I_TYPE',
             'JUMP': 'I_TYPE', 'JAL': 'I_TYPE',
             # R_TYPE
             'ADD': 'R_TYPE', 'SUB': 'R_TYPE', 'AND': 'R_TYPE', 'OR': 'R_TYPE', 
             'XOR': 'R_TYPE', 'MUL': 'R_TYPE', 'MOD': 'R_TYPE', 'MULMOD': 'R_TYPE',
             'ROTL': 'R_TYPE', 'ROTR': 'R_TYPE',
             # Añadidos shifts
             'SHIFTL': 'R_TYPE', 'SHIFTR': 'R_TYPE',
             # S_TYPE
             'STORE': 'S_TYPE', 'BEQ': 'S_TYPE', 'BNE': 'S_TYPE', 'BLT': 'S_TYPE',
             # V_TYPE (instrucciones de bóveda / vault)
             'VSTORE': 'V_TYPE', 'VINIT': 'V_TYPE',
             'KVW': 'V_TYPE', 'KVL': 'V_TYPE', 'VLOAD': 'V_TYPE', 'KVOP': 'V_TYPE', 'SGEN': 'V_TYPE',
             # H_TYPE
             'HASH_INIT': 'H_TYPE', 'HASH_BLOCK': 'H_TYPE', 'HASH_FINAL': 'H_TYPE',
             'SIGN': 'H_TYPE', 'VERIFY': 'H_TYPE'
         }
        
        return format_map.get(opcode_name, 'R_TYPE')  # Por defecto R_TYPE

    def get_metrics(self):
        return dict(self.metrics)