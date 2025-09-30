# isa_definition.py

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

def get_field_value(instruction, field_name, format_type):
    """Extrae el valor de un campo de una instrucción"""
    if format_type not in INST_FORMATS:
        raise ValueError(f"Formato no válido: {format_type}")
    
    fields = INST_FORMATS[format_type]['fields']
    if field_name not in fields:
        raise ValueError(f"Campo no válido: {field_name}")
    
    start, end = fields[field_name]
    mask = ((1 << (start - end + 1)) - 1) << end
    return (instruction & mask) >> end

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
            raise ValueError(f"Valor {value} excede los {field_bits} bits para {field_name}")
        
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