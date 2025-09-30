"""
Paquete 'isa' - inicializador mínimo.
Exporta nombres de módulos relevantes para facilitar imports del tipo:
  from isa.register_file import register_file
"""
# Minimal package init to simplify imports
from .isa_types import UInt64, Vec4x64
from .isa_definition import OPCODES, VAULT_SLOTS, TOYMDMA_CONSTANTS
__all__ = ['UInt64', 'Vec4x64', 'OPCODES', 'VAULT_SLOTS', 'TOYMDMA_CONSTANTS']
