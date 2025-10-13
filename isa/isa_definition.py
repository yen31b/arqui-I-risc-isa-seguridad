# isa_definition.py
import addressing_modes as addr_modes

# =============================================================================
# FORMATOS DE INSTRUCCIÓN (32 bits)
# =============================================================================

INST_FORMATS = {
    'R_TYPE': {
        'fields': {'opcode': (31, 26), 'rd': (25, 21), 'rs1': (20, 16), 'rs2': (15, 11), 'funct': (10, 0)},
        'description': 'Registro-Registro'
    },
    'I_TYPE': {
        'fields': {'opcode': (31, 26), 'rd': (25, 21), 'rs1': (20, 16), 'imm': (15, 0)},
        'description': 'Inmediato'
    },
    'S_TYPE': {
        'fields': {'opcode': (31, 26), 'rs1': (25, 21), 'rs2': (20, 16), 'imm': (15, 0)},
        'description': 'Store'
    },
    'V_TYPE': {
        'fields': {'opcode': (31, 26), 'vault_idx': (25, 21), 'rs1': (20, 16), 'funct': (15, 0)},
        'description': 'Bóveda'
    },
    'H_TYPE': {
        'fields': {'opcode': (31, 26), 'rs1': (25, 21), 'funct': (20, 0)},
        'description': 'Hash'
    }
}

# =============================================================================
# OPCODES (6 bits)
# =============================================================================

OPCODES = {
    # Operaciones Aritméticas-Lógicas
    'NOP':   0b000000,
    'ADD':   0b000001,
    'SUB':   0b000010,
    'AND':   0b000011,
    'OR':    0b000100,
    'XOR':   0b000101,
    'ADDI':  0b000110,
    'ANDI':  0b000111,

    # Operaciones de Memoria
    'LOAD':  0b001000,
    'STORE': 0b001001,
    'LOADI': 0b001010,  # Load Inmediato (para cargar constantes)

    # Control de Flujo
    'JUMP':  0b001100,
    'JAL':   0b001101,  # Jump and Link
    'BEQ':   0b001110,  # Branch if Equal
    'BNE':   0b001111,  # Branch if Not Equal
    'BLT':   0b010000,  # Branch if Less Than

    # Operaciones de Bóveda
    'VSTORE': 0b010100,  # Almacenar en bóveda
    'VINIT':  0b010101,  # Inicializar valores hash en bóveda

    # Operaciones de Hash
    'HASH_INIT':  0b011000,
    'HASH_BLOCK': 0b011001,
    'HASH_FINAL': 0b011010,

    # Mezclas No Lineales
    'CALC_F': 0b011110,
    'CALC_G': 0b011111,
    'CALC_H': 0b100110,

    # Operaciones de Firma Digital
    'SIGN':   0b011100,
    'VERIFY': 0b011101,

    # Multiplicación y Operaciones Especiales
    'MUL':    0b100000,
    'MOD':    0b100001,
    'MULMOD': 0b100010,  # Multiplicación modular (para ToyMDMA)

    # Operaciones de Rotación/Desplazamiento
    'ROTL':   0b100100,  # Rotate Left
    'ROTR':   0b100101,  # Rotate Right

    #Calcular abcd directamente
    'UPDATE_A': 0x3A,
    'UPDATE_B': 0x3B,
    'UPDATE_C': 0x3C,
    'UPDATE_D': 0x3D,

    # --- añadidos: operaciones de bóveda y hash específicas ---
    'VLOAD':  0b010001,   # (lectura administrativa / alias)
    'KVW':    0b010011,   # write autorizado a bóveda (alias interno)
    'KVL':    0b010110,   # lectura controlada de bóveda
    'KVOP':   0b010111,   # operación en llave mediante handle
    'SGEN':   0b011011,   # generación de firma atómica en bóveda

    # --- añadidos: operaciones de mezcla/no-lineal para ToyMDMA ---
    'MIXMUL': 0b100011,
    'MODADD': 0b100111,
    'NONLIN': 0b101000,
}

# =============================================================================
# REGISTROS (32 registros de 64 bits)
# =============================================================================

REGISTERS = {
    'R0': 0,   # Registro cero (siempre 0)
    'R1': 1,   'R2': 2,   'R3': 3,   'R4': 4,   'R5': 5,
    'R6': 6,   'R7': 7,   'R8': 8,   'R9': 9,   'R10': 10,
    'R11': 11, 'R12': 12, 'R13': 13, 'R14': 14, 'R15': 15,
    'R16': 16, 'R17': 17, 'R18': 18, 'R19': 19, 'R20': 20,
    'R21': 21, 'R22': 22, 'R23': 23, 'R24': 24, 'R25': 25,
    'R26': 26, 'R27': 27, 'R28': 28, 'R29': 29, 'R30': 30,
    'R31': 31,

    # Nombres especiales
    'SP': 29,  # Stack Pointer
    'FP': 30,  # Frame Pointer
    'RA': 31,  # Return Address
}

# =============================================================================
# FUNCT CODES (para operaciones especializadas)
# =============================================================================

FUNCT_CODES = {
    'HASH_START':   0b00000000001,
    'HASH_PROCESS': 0b00000000010,
    'HASH_END':     0b00000000011,

    'VAULT_KEY':    0b00000000100,  # Operar con llaves privadas
    'VAULT_HASH':   0b00000000101,  # Operar con valores hash iniciales
}

# =============================================================================
# CONSTANTES PARA BÓVEDA
# =============================================================================

VAULT_SLOTS = {
    'KEY_0': 0,    # Llave privada 0
    'KEY_1': 1,    # Llave privada 1
    'KEY_2': 2,    # Llave privada 2
    'KEY_3': 3,    # Llave privada 3

    'HASH_A': 4,   # Valor inicial A del hash
    'HASH_B': 5,   # Valor inicial B del hash
    'HASH_C': 6,   # Valor inicial C del hash
    'HASH_D': 7,   # Valor inicial D del hash
}

# =============================================================================
# CONSTANTES PARA TOYMDMA
# =============================================================================

TOYMDMA_CONSTANTS = {
    'GOLDEN_RATIO': 0x9e3779b97f4a7c15,
    'PRIME_MOD': 0xFFFFFFFB,
    'INITIAL_A': 0x6A09E667F3BCC908,
    'INITIAL_B': 0xBB67AE8584CAA73B,
    'INITIAL_C': 0x3C6EF372FE94F82B,
    'INITIAL_D': 0xA54FF53A5F1D36F1,
}

# =============================================================================
# FUNCIONES DE UTILIDAD
# =============================================================================


# En isa_definition.py - mejorar get_field_value

def get_field_value(instruction, field_name, format_type):
    """Extrae el valor de un campo de una instrucción - MEJORADO"""
    if format_type not in INST_FORMATS:
        raise ValueError(f"Formato no válido: {format_type}")

    fields = INST_FORMATS[format_type]['fields']
    if field_name not in fields:
        raise ValueError(f"Campo no válido: {field_name} para formato {format_type}")

    start, end = fields[field_name]
    field_width = start - end + 1
    mask = ((1 << field_width) - 1) << end
    value = (instruction & mask) >> end
    
    # Debug opcional
    # print(f"  📐 Extrayendo {field_name}: bits [{start}:{end}], valor={value}")
    
    return value

def encode_instruction(format_type, **fields):
    """Codifica una instrucción a partir de los campos"""
    if format_type not in INST_FORMATS:
        raise ValueError(f"Formato no válido: {format_type}")

    instruction = 0
    field_defs = INST_FORMATS[format_type]['fields']

    for field_name, value in fields.items():
        if field_name not in field_defs:
            raise ValueError(f"Campo no válido: {field_name}")

        start, end = field_defs[field_name]
        field_bits = start - end + 1
        max_value = (1 << field_bits) - 1

        if value > max_value:
            raise ValueError(
                f"Valor {value} excede los {field_bits} bits para {field_name}")

        instruction |= (value << end)

    return instruction


def instruction_to_string(instruction):
    """Convierte una instrucción a string legible (para debugging)"""
    opcode = get_field_value(instruction, 'opcode', 'R_TYPE')

    # Buscar el nombre del opcode
    opcode_name = 'UNKNOWN'
    for name, code in OPCODES.items():
        if code == opcode:
            opcode_name = name
            break

    return f"{opcode_name}: 0x{instruction:08x}"


# Registros
# → 32 registros generales de 64 bits: R0..R31 (R0 = constante cero por convención)
# → Registros especiales: PC (Program Counter, 64 bits), SR (Status Register, 64 bits)
REGISTERS_DECISION = {
    'general_count': 32,
    'general_width_bits': 64,
    'zero_register': 'R0',
    'special_registers': ['PC', 'SR']
}

# Tipos de datos
# → Principal: 64 bits (datos y llaves)
# → Especial: 256 bits representado como 4 × 64 bits (estado del hash A,B,C,D)
DATA_TYPES_DECISION = {
    'primary_bits': 64,
    'hash_state_bits': 256,
    'hash_state_words': 4
}

# Modos de direccionamiento (soportados)
# 1) Directo desde un registro (REG)
# 2) Registro + inmediato pequeño (REG_IMM)
# 3) Memoria con base + desplazamiento (BASE_DISP)
# 4) Número inmediato largo (IMM_LONG)
ADDRESSING_MODES_DECISION = ['REG', 'REG_IMM', 'BASE_DISP', 'IMM_LONG']
INSTRUCTION_ADDRESSING_MODES = {
    'LOAD': 'REG_IMM',
    'STORE': 'BASE_DISP',
    'ADDI': 'REG_IMM',
    'LOADI': 'IMM_LONG',
    'JUMP': 'IMM_LONG',
    'VSTORE': 'REG',
    'VINIT': 'REG',
    'SIGN': 'REG',
    'VLOAD': 'REG',
    'KVW': 'REG',
    'KVL': 'REG',
    'KVOP': 'REG',
    'SGEN': 'REG',
    'MIXMUL': 'R_TYPE',
    'MODADD': 'R_TYPE',
    'NONLIN': 'R_TYPE',
}

ADDRESSING_MODE_FORMAT_MAP = {
    'REG': ['R_TYPE', 'V_TYPE'],
    'REG_IMM': ['I_TYPE'],
    'BASE_DISP': ['S_TYPE'],
    'IMM_LONG': ['I_TYPE', 'H_TYPE'],
}
# Instrucciones especiales de hash (nombres funcionales)
# → MIXMUL: mezcla y multiplica
# → MODADD: suma con módulo
# → NONLIN: función no lineal
#HASH_INSTR_NAMES = ['MIXMUL', 'MODADD', 'NONLIN']
#HASH_INSTR_NAMES = ['MIXMUL', 'MODADD', 'NONLIN', 'CALC_F', 'CALC_G', 'CALC_H']
HASH_INSTR_NAMES = [
    'MIXMUL', 'MODADD', 'NONLIN',
    'CALC_F', 'CALC_G', 'CALC_H',
    'UPDATE_A', 'UPDATE_B', 'UPDATE_C', 'UPDATE_D'
]


# =============================================================================
# CONSTANTES PARA BÓVEDA (centralizadas)
# =============================================================================

# Lista canonical de instrucciones que acceden la bóveda
VAULT_INSTR_NAMES = {
    'VSTORE', 'VINIT', 'VLOAD', 'SIGN', 'VERIFY',
    'KVL', 'KVOP', 'KVW', 'SGEN'
}

# Decisiones/flags de seguridad relacionadas con acceso a la bóveda.
# Se puede ampliar con más claves (p.ej. políticas de autorización, latencias)
VAULT_SECURITY_DECISION = {
    'protect_slots_from_memory': True,   # las llaves no deben ser volcaras a memoria general
    'require_authorization_for_write': True,
    'allowed_ops': VAULT_INSTR_NAMES
}

# Rango de direcciones reservado para la bóveda (contrato global)
# Las etapas deben usar este rango para bloquear accesos por LOAD/STORE
VAULT_ADDR_RANGE = (0x1000, 0x1FFF)

# Instrucción de firma
# → SGEN: genera una firma combinando el estado hash (A,B,C,D) con una llave de la bóveda
SIGN_INSTR_NAME = 'SGEN'

# Formato de instrucción y codificación (decisión general)
# → Tamaño fijo de instrucción: 32 bits
# → Campos típicos sugeridos: opcode (6), rd (5), rs1 (5), rs2/imm (16) u otras variantes por formato
# → Se mantienen los formatos INST_FORMATS definidos anteriormente (R_TYPE, I_TYPE, S_TYPE, V_TYPE, H_TYPE)
INSTRUCTION_FORMAT_DECISION = {
    'width_bits': 32,
    'typical_fields': {'opcode': 6, 'rd': 5, 'rs1': 5, 'rs2_or_imm': 16},
    'use_existing_formats': True
}

# Restricciones de seguridad (reglas operativas)
# → La bóveda no puede leerse ni mapearse como memoria normal.
# → Solo las instrucciones especiales de bóveda y firma pueden acceder a los slots de la bóveda.
# → Las llaves privadas no pueden escribirse a registros generales ni a memoria por instrucciones normales.
VAULT_SECURITY_DECISION = {
    'no_memory_map': True,
    'only_special_instr_access': True,
    'no_register_exposure': True
}
# =============================================================================
# INTEGRACIÓN CON MODOS DE DIRECCIONAMIENTO
# =============================================================================


def apply_addressing_mode(instr_name, registers, **kwargs):
    """
    Aplica el modo de direccionamiento correspondiente a una instrucción.
    Utiliza las funciones definidas en addressing_modes.py.
    """
    mode = INSTRUCTION_ADDRESSING_MODES.get(instr_name)
    if not mode:
        raise ValueError(
            f"Instrucción {instr_name} no tiene modo de direccionamiento definido")

    if mode == 'REG':
        addr = addr_modes.mode_REG(registers, kwargs['rs1'])
    elif mode == 'REG_IMM':
        addr = addr_modes.mode_REG_IMM(registers, kwargs['rs1'], kwargs['imm'])
    elif mode == 'BASE_DISP':
        addr = addr_modes.mode_BASE_DISP(
            registers, kwargs['base_reg'], kwargs['disp_reg'])
    elif mode == 'IMM_LONG':
        addr = addr_modes.mode_IMM_LONG(kwargs['imm'])
    else:
        raise ValueError(f"Modo de direccionamiento desconocido: {mode}")

    # Validación de seguridad si se define un rango de bóveda
    vault_range = kwargs.get('vault_range')
    if vault_range:
        addr_modes.validate_address(addr, vault_range)

    return addr
