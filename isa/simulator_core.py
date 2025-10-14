from .isa_definition import (
    get_field_value, OPCODES, INST_FORMATS,
    apply_addressing_mode, instruction_to_string, VAULT_ADDR_RANGE
)
from .isa_types import UInt64
from .register_file import register_file
from .addressing_modes import validate_address

# Simulación de memoria simple (diccionario)
MEMORY = {}


def execute_instruction(instruction, registers):
    """
    Ejecuta una instrucción codificada de 32 bits.
    Soporta ADDI, LOAD, STORE.
    Aplica validaciones de seguridad contra la bóveda.
    """
    opcode = get_field_value(instruction, 'opcode', 'I_TYPE')

    # Buscar nombre de instrucción
    instr_name = next((name for name, code in OPCODES.items()
                      if code == opcode), 'UNKNOWN')
    print(f"Ejecutando: {instruction_to_string(instruction)}")

    try:
        if instr_name == 'ADDI':
            rd = f"R{get_field_value(instruction, 'rd', 'I_TYPE')}"
            rs1 = f"R{get_field_value(instruction, 'rs1', 'I_TYPE')}"
            imm = get_field_value(instruction, 'imm', 'I_TYPE')
            result = apply_addressing_mode('ADDI', registers, rs1=rs1, imm=imm)
            registers.write(rd, result)

        elif instr_name == 'LOAD':
            rd = f"R{get_field_value(instruction, 'rd', 'I_TYPE')}"
            rs1 = f"R{get_field_value(instruction, 'rs1', 'I_TYPE')}"
            imm = get_field_value(instruction, 'imm', 'I_TYPE')
            addr = apply_addressing_mode('LOAD', registers, rs1=rs1, imm=imm)

            # Validar dirección contra la bóveda
            validate_address(addr, VAULT_ADDR_RANGE)

            value = MEMORY.get(int(addr), UInt64(0))
            registers.write(rd, value)

        elif instr_name == 'STORE':
            rs1 = f"R{get_field_value(instruction, 'rs1', 'S_TYPE')}"
            rs2 = f"R{get_field_value(instruction, 'rs2', 'S_TYPE')}"
            imm = get_field_value(instruction, 'imm', 'S_TYPE')

            # Dirección = rs1 + imm
            addr = apply_addressing_mode('STORE', registers, base_reg=rs1, disp_reg=rs2)            # Validar dirección contra la bóveda
            validate_address(addr, VAULT_ADDR_RANGE)

            value = registers.read(rs2)  # CORREGIDO: se guarda el valor de rs2
            MEMORY[int(addr)] = UInt64(value)

        else:
            print(f"Instrucción no soportada: {instr_name}")

    except PermissionError as e:
        print(f"🛑 Violación de seguridad: {e}")
