"""Compatibilidad retro: reexporta símbolos desde ``simple_assembler.assembler``."""

from .assembler import Assembler, AssemblyError, format_words

__all__ = ["Assembler", "AssemblyError", "format_words"]
