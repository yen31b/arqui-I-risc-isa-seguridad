"""
addressing_modes.py

Funciones helper para calcular direcciones según los modos soportados por la ISA.
Expectativas importantes:
 - 'registers' es el objeto de banco de registros (register_file) y debe proveer
   read(name) retornando un entero o UInt64 convertible a int().
 - Las funciones retornan UInt64 (o int-convertible) representando la dirección.
 - validate_address acepta una dirección (UInt64 o int) y opcionalmente un
   rango de la bóveda para verificar accesos prohibidos.
"""

from isa_types import UInt64


def mode_REG(registers, rs1):
    """
    Modo REG: acceso directo al valor de un registro.
    """
    return UInt64(registers.read(rs1))


def mode_REG_IMM(registers, rs1, imm):
    """
    Modo REG_IMM: suma de registro base + inmediato pequeño.
    """
    base = registers.read(rs1)
    offset = imm & 0xFFFF  # 16 bits
    return UInt64(base + offset)


def mode_BASE_DISP(registers, base_reg, disp_reg):
    """
    Modo BASE_DISP: dirección calculada como base + desplazamiento.
    """
    base = registers.read(base_reg)
    disp = registers.read(disp_reg)
    return UInt64(base + disp)


def mode_IMM_LONG(imm):
    """
    Modo IMM_LONG: uso directo de un valor inmediato largo.
    """
    return UInt64(imm & 0xFFFFFFFFFFFFFFFF)  # 64 bits


def validate_address(address, vault_range=None):
    """
    Valida que la dirección no acceda a zonas restringidas como la bóveda.
    - address: puede ser UInt64 o int; se convierte internamente a int().
    - vault_range: tupla (start, end) si se quiere bloquear un rango.
    Lanza PermissionError si la dirección cae dentro del rango prohibido.
    """
    addr = int(address)
    if vault_range and vault_range[0] <= addr <= vault_range[1]:
        raise PermissionError(
            "Acceso ilegal a bóveda mediante direccionamiento")
    return True


def describe_addressing(mode_name, **kwargs):
    """
    Devuelve una descripción textual del modo de direccionamiento aplicado.
    """
    if mode_name == 'REG':
        return f"[{kwargs['rs1']}]"
    elif mode_name == 'REG_IMM':
        return f"[{kwargs['rs1']} + {kwargs['imm']}]"
    elif mode_name == 'BASE_DISP':
        return f"[{kwargs['base_reg']} + {kwargs['disp_reg']}]"
    elif mode_name == 'IMM_LONG':
        return f"{kwargs['imm']}"
    else:
        return "Modo desconocido"
