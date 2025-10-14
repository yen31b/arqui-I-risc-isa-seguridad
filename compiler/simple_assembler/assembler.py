"""Ensamblador simple de 32 bits

Formato de instrucción (31..0):
    31-28 : opcode (4 bits)
    27-25 : registro destino (3 bits)
    24-22 : registro fuente A (3 bits)
    21-19 : registro fuente B (3 bits)
    18-0  : inmediato (19 bits) o relleno

Se soportan los formatos:
- R: 3 registros, inmediato en cero
- I: registro destino, registro base y literal de 19 bits con signo
- J: salto absoluto de 22 bits
- B: rama relativa con offset de 19 bits con signo
- W: directiva .word

El objetivo es ilustrar un ensamblador didáctico; ajusta los formatos a tu ISA.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

__all__ = ["Assembler", "AssemblyError", "format_words"]


class AssemblyError(Exception):
    """Error semántico durante el ensamblado."""

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


@dataclass(frozen=True)
class InstructionSpec:
    opcode: int
    fmt: str  # "R", "I", "J", "B", "W"


REGISTERS: Dict[str, int] = {f"R{i}": i for i in range(8)}

INSTRUCTION_SET: Dict[str, InstructionSpec] = {
    "NOP": InstructionSpec(0x0, "R"),
    "ADD": InstructionSpec(0x1, "R"),
    "SUB": InstructionSpec(0x2, "R"),
    "XOR": InstructionSpec(0x3, "R"),
    "LOAD": InstructionSpec(0x4, "I"),   # LOAD RD, RS, IMM => RD = MEM[RS + IMM]
    "STORE": InstructionSpec(0x5, "I"),  # STORE RS, RD, IMM => MEM[RD + IMM] = RS
    "ADDI": InstructionSpec(0x6, "I"),   # ADDI RD, RS, IMM
    "JMP": InstructionSpec(0x7, "J"),    # JMP etiqueta/inmediato
    "BEQ": InstructionSpec(0x8, "B"),    # BEQ RS, RT, etiqueta
    "HALT": InstructionSpec(0xF, "R"),
    ".WORD": InstructionSpec(0x0, "W"),
}

COMMENT_CHARS = ("#", ";", "//")


class Assembler:
    """Traduce líneas de texto ensamblador a palabras binarias de 32 bits."""

    def assemble(self, source: str) -> List[int]:
        parsed, labels = self._first_pass(source)
        words: List[int] = []
        for pc, line in enumerate(parsed):
            words.append(self._encode(line, labels, pc))
        return words

    def assemble_to_strings(self, source: str) -> List[str]:
        return [format(word & 0xFFFFFFFF, "032b") for word in self.assemble(source)]

    def assemble_file(self, path: str, encoding: str = "utf-8") -> List[int]:
        with open(path, "r", encoding=encoding) as handle:
            return self.assemble(handle.read())

    # ------------------ primera pasada ------------------

    def _first_pass(self, source: str) -> Tuple[List[ParsedLine], Dict[str, int]]:
        parsed: List[ParsedLine] = []
        labels: Dict[str, int] = {}
        pc = 0
        for idx, raw in enumerate(source.splitlines(), start=1):
            clean = self._strip_comments(raw)
            if not clean.strip():
                continue

            label, remainder = self._split_label(clean)
            if label:
                if label in labels:
                    raise AssemblyError(f"Etiqueta duplicada '{label}'", line_no=idx, line_text=raw)
                labels[label] = pc
            if not remainder.strip():
                continue

            mnemonic, operands = self._parse_tokens(remainder, idx, raw)
            parsed.append(ParsedLine(idx, mnemonic, operands, raw.rstrip("\n")))
            pc += 1

        return parsed, labels

    def _strip_comments(self, line: str) -> str:
        for marker in COMMENT_CHARS:
            if marker in line:
                line = line.split(marker, 1)[0]
        return line

    def _split_label(self, line: str) -> Tuple[str | None, str]:
        if ":" not in line:
            return None, line
        label, rest = line.split(":", 1)
        label = label.strip()
        rest = rest.strip()
        return (label or None), rest

    def _parse_tokens(self, text: str, line_no: int, raw: str) -> Tuple[str, Tuple[str, ...]]:
        tokens = [tok.strip() for tok in text.replace(",", " ").split() if tok.strip()]
        if not tokens:
            raise AssemblyError("Instrucción vacía", line_no=line_no, line_text=raw)
        mnemonic = tokens[0].upper()
        operands = tuple(tokens[1:])
        return mnemonic, operands

    # ------------------ codificación ------------------

    def _encode(self, line: ParsedLine, labels: Dict[str, int], pc: int) -> int:
        spec = INSTRUCTION_SET.get(line.mnemonic)
        if spec is None:
            raise AssemblyError(f"Instrucción desconocida '{line.mnemonic}'", line_no=line.line_no, line_text=line.raw)

        if spec.fmt == "W":
            if len(line.operands) != 1:
                raise AssemblyError(".word espera un operando", line_no=line.line_no, line_text=line.raw)
            value = self._resolve_value(line.operands[0], labels, bits=32, signed=True, current_pc=pc, line=line)
            return value & 0xFFFFFFFF

        opcode = spec.opcode << 28

        if spec.fmt == "R":
            self._assert_operands(line, 3)
            rd = self._parse_reg(line.operands[0], line)
            rs = self._parse_reg(line.operands[1], line)
            rt = self._parse_reg(line.operands[2], line)
            return opcode | (rd << 25) | (rs << 22) | (rt << 19)

        if spec.fmt == "I":
            self._assert_operands(line, 3)
            rd = self._parse_reg(line.operands[0], line)
            rs = self._parse_reg(line.operands[1], line)
            imm = self._resolve_value(line.operands[2], labels, bits=19, signed=True, current_pc=pc, line=line)
            return opcode | (rd << 25) | (rs << 22) | (imm & 0x7FFFF)

        if spec.fmt == "J":
            self._assert_operands(line, 1)
            target = self._resolve_value(line.operands[0], labels, bits=22, signed=False, current_pc=pc, line=line)
            return opcode | (target & 0x3FFFFF)

        if spec.fmt == "B":
            self._assert_operands(line, 3)
            rs = self._parse_reg(line.operands[0], line)
            rt = self._parse_reg(line.operands[1], line)
            offset = self._resolve_branch(line.operands[2], labels, pc)
            return opcode | (rs << 22) | (rt << 19) | (offset & 0x7FFFF)

        raise AssemblyError(f"Formato no soportado '{spec.fmt}'", line_no=line.line_no, line_text=line.raw)

    def _assert_operands(self, line: ParsedLine, expected: int) -> None:
        if len(line.operands) != expected:
            raise AssemblyError(
                f"'{line.mnemonic}' espera {expected} operando(s)",
                line_no=line.line_no,
                line_text=line.raw,
            )

    def _parse_reg(self, token: str, line: ParsedLine) -> int:
        reg = token.upper()
        if reg not in REGISTERS:
            raise AssemblyError(f"Registro inválido '{token}'", line_no=line.line_no, line_text=line.raw)
        return REGISTERS[reg]

    def _resolve_branch(self, token: str, labels: Dict[str, int], pc: int) -> int:
        if token in labels:
            target = labels[token]
            offset = target - (pc + 1)
        else:
            offset = self._parse_int(token, bits=19, signed=True)
        if not (-(1 << 18) <= offset <= (1 << 18) - 1):
            raise AssemblyError(
                f"Offset fuera de rango para 19 bits con signo: {offset}",
                line_no=None,
                line_text=None,
            )
        return offset & 0x7FFFF

    def _resolve_value(
        self,
        token: str,
        labels: Dict[str, int],
        *,
        bits: int,
        signed: bool,
        current_pc: int,
        line: ParsedLine,
    ) -> int:
        if token in labels:
            value = labels[token]
        else:
            value = self._parse_int(token, bits=bits, signed=signed)
        min_val = -(1 << (bits - 1)) if signed else 0
        max_val = (1 << (bits - 1)) - 1 if signed else (1 << bits) - 1
        if not (min_val <= value <= max_val):
            tipo = "con signo" if signed else "sin signo"
            raise AssemblyError(
                f"Valor fuera de rango ({value}) para {bits} bits {tipo}",
                line_no=line.line_no,
                line_text=line.raw,
            )
        return value & ((1 << bits) - 1)

    def _parse_int(self, token: str, *, bits: int, signed: bool) -> int:
        token_clean = token.replace("_", "")
        base = 10
        if token_clean.startswith("0x"):
            base = 16
        elif token_clean.startswith("0b"):
            base = 2
        elif token_clean.startswith("0o"):
            base = 8
        value = int(token_clean, base)
        if signed and value < 0:
            min_val = -(1 << (bits - 1))
            if value < min_val:
                raise AssemblyError(f"Valor negativo fuera de rango: {value}")
        return value


def format_words(words: Sequence[int], *, fmt: str = "bin") -> List[str]:
    fmt_lower = fmt.lower()
    if fmt_lower == "bin":
        return [format(word & 0xFFFFFFFF, "032b") for word in words]
    if fmt_lower == "hex":
        return [f"0x{word & 0xFFFFFFFF:08X}" for word in words]
    if fmt_lower == "int":
        return [str(word & 0xFFFFFFFF) for word in words]
    raise ValueError("Formatos soportados: bin, hex, int")
