"""Assembler que utiliza la definición formal de la ISA del proyecto.

La implementación realiza dos pasadas para resolver etiquetas y soporta los
formatos declarados en ``isa_definition.INST_FORMATS`` (R/I/S/V/H de 32 bits).

Sintaxis soportada (resumen):

* Instrucciones R-Type (3 registros): ``ADD R1, R2, R3``.
  - Puede agregarse un cuarto operando para el campo ``funct`` (número o
    símbolo definido en ``FUNCT_CODES``).
* Inmediatos: ``ADDI R1, R2, -4`` o ``LOADI R3, 0xFF``.
* Memoria: ``LOAD R1, R2, 16`` y ``STORE R2, R3, 0``.
* Saltos/ramas: ``BEQ R1, R2, etiqueta``; ``JUMP destino``; ``JAL R31, label``.
* Bóveda/hash: ``VSTORE KEY_0, R1``; ``HASH_INIT R2``; se aceptan los nombres de
  ``VAULT_SLOTS`` y ``FUNCT_CODES``.
* Directiva ``.word`` para insertar palabras de 32 bits sin procesar.

Los valores simbólicos (registros, slots, funct) no distinguen mayúsculas y
pueden escribirse con guiones bajos para mejorar legibilidad.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence, Tuple

from isa import isa_definition as ISA

COMMENT_MARKERS: Tuple[str, ...] = ("#", ";", "//")

# Conjuntos de instrucciones por tipo de tratamiento
R_TYPE_OPS = {
    "NOP",
    "ADD",
    "SUB",
    "AND",
    "OR",
    "XOR",
    "MUL",
    "MOD",
    "MULMOD",
    "MIXMUL",
    "MODADD",
    "ROTL",
    "ROTR",
    "SHIFTL",
    "SHIFTR",
    "NONLIN",
    "CALC_F",
    "CALC_G",
    "CALC_H",
}
I_REG_IMM_OPS = {"ADDI", "ANDI", "LOAD"}
S_TYPE_STORE_OPS = {"STORE"}
BRANCH_OPS = {"BEQ", "BNE", "BLT"}
UPDATE_OPS = {"UPDATE_A", "UPDATE_B", "UPDATE_C", "UPDATE_D"}
V_TYPE_OPS = {"VSTORE", "VINIT", "VLOAD", "KVW", "KVL", "KVOP", "SGEN"}
H_TYPE_OPS = {"HASH_INIT", "HASH_BLOCK", "HASH_FINAL", "SIGN", "VERIFY"}

FUNCT_DEFAULTS: Dict[str, int] = {
    "HASH_INIT": ISA.FUNCT_CODES.get("HASH_START", 0),
    "HASH_BLOCK": ISA.FUNCT_CODES.get("HASH_PROCESS", 0),
    "HASH_FINAL": ISA.FUNCT_CODES.get("HASH_END", 0),
    "SIGN": ISA.FUNCT_CODES.get("VAULT_KEY", 0),
    "VERIFY": ISA.FUNCT_CODES.get("VAULT_HASH", 0),
    "VSTORE": ISA.FUNCT_CODES.get("VAULT_KEY", 0),
    "VINIT": ISA.FUNCT_CODES.get("VAULT_HASH", 0),
}

VAULT_SLOT_MAP: Dict[str, int] = {}
for name, index in ISA.VAULT_SLOTS.items():
    upper = name.upper()
    VAULT_SLOT_MAP[upper] = index
    VAULT_SLOT_MAP[upper.replace("_", "")] = index
REGISTER_MAP = {name.upper(): value for name, value in ISA.REGISTERS.items()}

SYMBOLIC_CONSTANTS: Dict[str, int] = {}

def _register_constant(name: str, value: int) -> None:
    upper = name.upper()
    SYMBOLIC_CONSTANTS[upper] = int(value)
    SYMBOLIC_CONSTANTS[upper.replace("_", "")] = int(value)


for mapping in (
    getattr(ISA, "TOYMDMA_CONSTANTS", {}),
    getattr(ISA, "VAULT_SLOTS", {}),
):
    for const_name, const_value in mapping.items():
        _register_constant(const_name, const_value)

R_TYPE_OPERAND_COUNTS: Dict[str, int] = {mnemonic: 3 for mnemonic in R_TYPE_OPS}
R_TYPE_OPERAND_COUNTS["NONLIN"] = 2


class AssemblyError(Exception):
    """Error especializado que incluye número de línea e instrucción original."""

    def __init__(self, message: str, *, line_no: int | None = None, line_text: str | None = None) -> None:
        super().__init__(message)
        self.line_no = line_no
        self.line_text = line_text

    def __str__(self) -> str:
        base = super().__str__()
        if self.line_no is None:
            return base
        snippet = f"\n    {self.line_text}" if self.line_text else ""
        return f"Línea {self.line_no}: {base}{snippet}"


@dataclass(frozen=True)
class ParsedLine:
    line_no: int
    mnemonic: str
    operands: Tuple[str, ...]
    raw: str


class Assembler:
    """Convierte código ensamblador del ISA oficial en palabras de 32 bits."""

    def __init__(self, *, base_address: int = 0) -> None:
        self.base_address = base_address

    def assemble(self, source: str) -> List[int]:
        instructions, labels = self._first_pass(source)
        words: List[int] = []
        for idx, parsed in enumerate(instructions):
            address = self.base_address + idx
            words.append(self._encode(parsed, labels, address))
        return words

    def assemble_file(self, path: str, encoding: str = "utf-8") -> List[int]:
        with open(path, "r", encoding=encoding) as handle:
            return self.assemble(handle.read())

    def assemble_to_strings(self, source: str, fmt: str = "hex") -> List[str]:
        words = self.assemble(source)
        return format_words(words, fmt=fmt)

    # ------------------------------------------------------------------
    # Primera pasada: limpieza de comentarios, captura de etiquetas
    # ------------------------------------------------------------------

    def _first_pass(self, source: str) -> Tuple[List[ParsedLine], Dict[str, int]]:
        instructions: List[ParsedLine] = []
        labels: Dict[str, int] = {}
        address = self.base_address

        for idx, raw_line in enumerate(source.splitlines(), start=1):
            line = self._strip_comment(raw_line)
            if not line.strip():
                continue

            label, remainder = self._split_label(line)
            if label is not None:
                label_upper = label.upper()
                if label_upper in labels:
                    raise AssemblyError(f"Etiqueta duplicada '{label}'", line_no=idx, line_text=raw_line)
                labels[label_upper] = address
            if not remainder.strip():
                continue

            mnemonic, operands = self._parse_instruction(remainder, idx, raw_line)
            instructions.append(ParsedLine(idx, mnemonic, operands, raw_line.rstrip("\n")))
            address += 1

        return instructions, labels

    def _strip_comment(self, line: str) -> str:
        for marker in COMMENT_MARKERS:
            comment_pos = line.find(marker)
            if comment_pos != -1:
                line = line[:comment_pos]
        return line

    def _split_label(self, line: str) -> Tuple[str | None, str]:
        if ":" not in line:
            return None, line
        label, remainder = line.split(":", 1)
        label = label.strip()
        remainder = remainder.strip()
        return (label if label else None), remainder

    def _parse_instruction(self, text: str, line_no: int, raw_line: str) -> Tuple[str, Tuple[str, ...]]:
        parts = [token.strip() for token in text.replace(",", " ").split() if token.strip()]
        if not parts:
            raise AssemblyError("Instrucción vacía", line_no=line_no, line_text=raw_line)
        mnemonic = parts[0].upper()
        operands: Tuple[str, ...] = tuple(parts[1:])
        return mnemonic, operands

    # ------------------------------------------------------------------
    # Codificación
    # ------------------------------------------------------------------

    def _encode(self, line: ParsedLine, labels: Dict[str, int], address: int) -> int:
        mnemonic = line.mnemonic

        if mnemonic == ".WORD":
            if len(line.operands) != 1:
                raise AssemblyError(".word espera un operando", line_no=line.line_no, line_text=line.raw)
            value = self._resolve_immediate(line.operands[0], bits=32, signed=False, labels=labels, allow_label=True)
            return value & 0xFFFFFFFF

        if mnemonic not in ISA.OPCODES:
            raise AssemblyError(f"Instrucción desconocida '{mnemonic}'", line_no=line.line_no, line_text=line.raw)

        opcode = ISA.OPCODES[mnemonic]

        if mnemonic == "NOP":
            return ISA.encode_instruction("R_TYPE", opcode=opcode, rd=0, rs1=0, rs2=0, funct=0)

        if mnemonic in UPDATE_OPS:
            return self._encode_update(line, opcode)

        if mnemonic in R_TYPE_OPS:
            return self._encode_r_type(line, opcode)

        if mnemonic in I_REG_IMM_OPS:
            return self._encode_i_type_reg_imm(line, opcode)

        if mnemonic == "LOADI":
            return self._encode_loadi(line, opcode)

        if mnemonic == "JUMP":
            return self._encode_jump(line, opcode, labels)

        if mnemonic == "JAL":
            return self._encode_jal(line, opcode, labels)

        if mnemonic in S_TYPE_STORE_OPS:
            return self._encode_store(line, opcode)

        if mnemonic in BRANCH_OPS:
            return self._encode_branch(line, opcode, labels, address)

        if mnemonic in V_TYPE_OPS:
            return self._encode_v_type(line, opcode)

        if mnemonic in H_TYPE_OPS:
            return self._encode_h_type(line, opcode)

        raise AssemblyError(f"Formato no soportado para '{mnemonic}'", line_no=line.line_no, line_text=line.raw)

    def _encode_update(self, line: ParsedLine, opcode: int) -> int:
        if len(line.operands) not in (5, 6):
            raise AssemblyError(
                "UPDATE_* espera 'rd, rs1, rs2, rs3, rs4[, extra]'",
                line_no=line.line_no,
                line_text=line.raw,
            )

        rd = self._parse_register(line.operands[0], line)
        rs1 = self._parse_register(line.operands[1], line)
        rs2 = self._parse_register(line.operands[2], line)
        rs3 = self._parse_register(line.operands[3], line)
        rs4 = self._parse_register(line.operands[4], line)

        funct = ((rs3 & 0x1F) << 5) | (rs4 & 0x1F)

        if len(line.operands) == 6:
            extra_bits = self._resolve_immediate(line.operands[5], bits=11, signed=False)
            funct = (funct | extra_bits) & 0x7FF

        return ISA.encode_instruction(
            "R_TYPE",
            opcode=opcode,
            rd=rd,
            rs1=rs1,
            rs2=rs2,
            funct=funct,
        )

    def _encode_r_type(self, line: ParsedLine, opcode: int) -> int:
        expected_regs = R_TYPE_OPERAND_COUNTS.get(line.mnemonic, 3)
        if len(line.operands) not in (expected_regs, expected_regs + 1):
            raise AssemblyError(
                f"{line.mnemonic} espera {expected_regs} registros" + (" más funct opcional" if expected_regs != len(line.operands) else ""),
                line_no=line.line_no,
                line_text=line.raw,
            )
        rd = self._parse_register(line.operands[0], line)
        rs1 = self._parse_register(line.operands[1], line)
        if expected_regs >= 2:
            rs2_token_index = 2 if expected_regs >= 3 else None
        else:
            rs2_token_index = None
        if rs2_token_index is not None:
            rs2 = self._parse_register(line.operands[rs2_token_index], line)
        else:
            rs2 = 0
        if len(line.operands) == expected_regs + 1:
            funct = self._resolve_funct(line.operands[-1], line)
        else:
            funct = FUNCT_DEFAULTS.get(line.mnemonic, 0)
        return ISA.encode_instruction("R_TYPE", opcode=opcode, rd=rd, rs1=rs1, rs2=rs2, funct=funct & 0x7FF)

    def _encode_i_type_reg_imm(self, line: ParsedLine, opcode: int) -> int:
        if line.mnemonic == "LOAD" and len(line.operands) == 2:
            rd = self._parse_register(line.operands[0], line)
            rs1, imm = self._parse_memory_token(line.operands[1], line)
        else:
            if len(line.operands) != 3:
                raise AssemblyError("Formato I espera 3 operandos", line_no=line.line_no, line_text=line.raw)
            rd = self._parse_register(line.operands[0], line)
            rs1 = self._parse_register(line.operands[1], line)
            imm = self._resolve_immediate(line.operands[2], bits=16, signed=True)
        return ISA.encode_instruction("I_TYPE", opcode=opcode, rd=rd, rs1=rs1, imm=imm & 0xFFFF)

    def _encode_loadi(self, line: ParsedLine, opcode: int) -> int:
        if len(line.operands) not in (2, 3):
            raise AssemblyError("LOADI espera 'rd, [rs1,] imm'", line_no=line.line_no, line_text=line.raw)
        rd = self._parse_register(line.operands[0], line)
        if len(line.operands) == 3:
            rs1_token = line.operands[1]
            imm_token = line.operands[2]
            rs1 = self._parse_register(rs1_token, line)
        else:
            rs1 = REGISTER_MAP.get("R0", 0)
            imm_token = line.operands[1]
        imm = self._resolve_immediate(imm_token, bits=16, signed=True)
        return ISA.encode_instruction("I_TYPE", opcode=opcode, rd=rd, rs1=rs1, imm=imm & 0xFFFF)

    def _encode_jump(self, line: ParsedLine, opcode: int, labels: Dict[str, int]) -> int:
        if len(line.operands) != 1:
            raise AssemblyError("JUMP espera un único destino", line_no=line.line_no, line_text=line.raw)
        target = self._resolve_immediate(line.operands[0], bits=16, signed=False, labels=labels, allow_label=True)
        return ISA.encode_instruction("I_TYPE", opcode=opcode, rd=0, rs1=0, imm=target & 0xFFFF)

    def _encode_jal(self, line: ParsedLine, opcode: int, labels: Dict[str, int]) -> int:
        if len(line.operands) == 1:
            rd = REGISTER_MAP.get("RA", REGISTER_MAP.get("R31", 31))
            target_token = line.operands[0]
        elif len(line.operands) == 2:
            rd = self._parse_register(line.operands[0], line)
            target_token = line.operands[1]
        else:
            raise AssemblyError("JAL espera '[rd,] destino'", line_no=line.line_no, line_text=line.raw)
        target = self._resolve_immediate(target_token, bits=16, signed=False, labels=labels, allow_label=True)
        return ISA.encode_instruction("I_TYPE", opcode=opcode, rd=rd, rs1=0, imm=target & 0xFFFF)

    def _encode_store(self, line: ParsedLine, opcode: int) -> int:
        if len(line.operands) == 2:
            rs2 = self._parse_register(line.operands[0], line)
            rs1, imm = self._parse_memory_token(line.operands[1], line)
        elif len(line.operands) == 3:
            rs1 = self._parse_register(line.operands[0], line)
            rs2 = self._parse_register(line.operands[1], line)
            imm = self._resolve_immediate(line.operands[2], bits=16, signed=True)
        else:
            raise AssemblyError(
                "STORE espera 'base, src, offset' o 'src, offset(base)'",
                line_no=line.line_no,
                line_text=line.raw,
            )
        return ISA.encode_instruction("S_TYPE", opcode=opcode, rs1=rs1, rs2=rs2, imm=imm & 0xFFFF)

    def _encode_branch(self, line: ParsedLine, opcode: int, labels: Dict[str, int], address: int) -> int:
        if len(line.operands) != 3:
            raise AssemblyError("Las ramas esperan 'rs1, rs2, destino'", line_no=line.line_no, line_text=line.raw)
        rs1 = self._parse_register(line.operands[0], line)
        rs2 = self._parse_register(line.operands[1], line)
        offset = self._resolve_branch_offset(line.operands[2], labels, current_address=address)
        return ISA.encode_instruction("S_TYPE", opcode=opcode, rs1=rs1, rs2=rs2, imm=offset & 0xFFFF)

    def _encode_v_type(self, line: ParsedLine, opcode: int) -> int:
        if len(line.operands) not in (2, 3):
            raise AssemblyError("VSTORE/VINIT esperan 'slot, rs1 [, funct]'", line_no=line.line_no, line_text=line.raw)
        slot = self._resolve_vault_slot(line.operands[0], line)
        rs1 = self._parse_register(line.operands[1], line)
        if len(line.operands) == 3:
            funct = self._resolve_funct(line.operands[2], line)
        else:
            funct = FUNCT_DEFAULTS.get(line.mnemonic, 0)
        return ISA.encode_instruction("V_TYPE", opcode=opcode, vault_idx=slot, rs1=rs1, funct=funct & 0xFFFF)

    def _encode_h_type(self, line: ParsedLine, opcode: int) -> int:
        if len(line.operands) not in (0, 1, 2):
            raise AssemblyError("Instrucciones HASH/SIGN aceptan hasta dos operandos", line_no=line.line_no, line_text=line.raw)
        if len(line.operands) >= 1:
            rs1 = self._parse_register(line.operands[0], line)
        else:
            rs1 = 0
        if len(line.operands) == 2:
            funct = self._resolve_funct(line.operands[1], line)
        else:
            funct = FUNCT_DEFAULTS.get(line.mnemonic, 0)
        return ISA.encode_instruction("H_TYPE", opcode=opcode, rs1=rs1, funct=funct & 0x1FFFFF)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _parse_register(self, token: str, line: ParsedLine) -> int:
        key = token.upper()
        if key not in REGISTER_MAP:
            raise AssemblyError(f"Registro inválido '{token}'", line_no=line.line_no, line_text=line.raw)
        return REGISTER_MAP[key]

    def _resolve_immediate(
        self,
        token: str,
        *,
        bits: int,
        signed: bool,
        labels: Dict[str, int] | None = None,
        allow_label: bool = False,
    ) -> int:
        token_clean = token.replace("_", "")
        key_upper = token_clean.upper()

        if key_upper in SYMBOLIC_CONSTANTS:
            return SYMBOLIC_CONSTANTS[key_upper]

        if allow_label and labels is not None:
            label_key = token_clean.upper()
            if label_key in labels:
                return labels[label_key]
        try:
            value = int(token_clean, 0)
        except ValueError as exc:
            raise AssemblyError(f"Literal inválido '{token}'", line_no=None) from exc
        min_val = -(1 << (bits - 1)) if signed else 0
        max_val = (1 << (bits - 1)) - 1 if signed else (1 << bits) - 1
        if not (min_val <= value <= max_val):
            rango = f"[{min_val}, {max_val}]" if signed else f"[0, {max_val}]"
            raise AssemblyError(f"Valor {value} fuera de rango para {bits} bits {('con' if signed else 'sin')} signo ({rango})")
        return value & ((1 << bits) - 1)

    def _parse_memory_token(self, token: str, line: ParsedLine) -> Tuple[int, int]:
        if "(" not in token or not token.endswith(")"):
            raise AssemblyError(
                "Operando de memoria inválido, usa offset(base)",
                line_no=line.line_no,
                line_text=line.raw,
            )
        offset_part, base_part = token.split("(", 1)
        base_name = base_part[:-1].strip()
        if not base_name:
            raise AssemblyError("Se requiere registro base en la dirección", line_no=line.line_no, line_text=line.raw)
        offset_token = offset_part.strip() or "0"
        rs1 = self._parse_register(base_name, line)
        imm = self._resolve_immediate(offset_token, bits=16, signed=True)
        return rs1, imm

    def _resolve_branch_offset(self, token: str, labels: Dict[str, int], *, current_address: int) -> int:
        label_key = token.replace("_", "").upper()
        if label_key in labels:
            target = labels[label_key]
            offset = target - (current_address + 1)
        else:
            offset = self._resolve_immediate(token, bits=16, signed=True)
        if not (-(1 << 15) <= offset <= (1 << 15) - 1):
            raise AssemblyError(f"Offset fuera de rango para rama: {offset}")
        return offset & 0xFFFF

    def _resolve_vault_slot(self, token: str, line: ParsedLine) -> int:
        key_raw = token.upper()
        key_compact = token.replace("_", "").upper()
        if key_raw in VAULT_SLOT_MAP:
            return VAULT_SLOT_MAP[key_raw]
        if key_compact in VAULT_SLOT_MAP:
            return VAULT_SLOT_MAP[key_compact]
        try:
            slot = int(token, 0)
        except ValueError as exc:
            raise AssemblyError(f"Slot de bóveda inválido '{token}'", line_no=line.line_no, line_text=line.raw) from exc
        if not (0 <= slot < 32):
            raise AssemblyError("Índice de bóveda fuera de rango (0-31)", line_no=line.line_no, line_text=line.raw)
        return slot

    def _resolve_funct(self, token: str, line: ParsedLine) -> int:
        key_raw = token.upper()
        key_compact = token.replace("_", "").upper()
        if key_raw in ISA.FUNCT_CODES:
            return ISA.FUNCT_CODES[key_raw]
        if key_compact in ISA.FUNCT_CODES:
            return ISA.FUNCT_CODES[key_compact]
        try:
            return int(token, 0)
        except ValueError as exc:
            raise AssemblyError(f"FUNCT inválido '{token}'", line_no=line.line_no, line_text=line.raw) from exc


def format_words(words: Sequence[int], *, fmt: str = "hex") -> List[str]:
    fmt_lower = fmt.lower()
    if fmt_lower == "hex":
        return [f"0x{word & 0xFFFFFFFF:08X}" for word in words]
    if fmt_lower == "bin":
        return [format(word & 0xFFFFFFFF, "032b") for word in words]
    if fmt_lower == "int":
        return [str(word & 0xFFFFFFFF) for word in words]
    raise ValueError("Formatos soportados: hex, bin, int")


__all__ = ["Assembler", "AssemblyError", "format_words"]
