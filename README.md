# 🟩 Green Card – Resumen Rápido

## Registros
- 32 registros de 64 bits: `R0`–`R31`
- `R0=0`, `SP=R29`, `FP=R30`, `RA=R31`

---

## Instrucciones Aritméticas / Lógicas
| Instrucción | Sintaxis | Operación |
|-------------|----------|-----------|
| ADD         | `ADD rd, rs1, rs2` | rd = rs1 + rs2 |
| SUB         | `SUB rd, rs1, rs2` | rd = rs1 - rs2 |
| AND         | `AND rd, rs1, rs2` | rd = rs1 & rs2 |
| OR          | `OR rd, rs1, rs2`  | rd = rs1 \| rs2 |
| XOR         | `XOR rd, rs1, rs2` | rd = rs1 ^ rs2 |
| ADDI        | `ADDI rd, rs1, imm` | rd = rs1 + imm |

---

## Memoria
| Instrucción | Sintaxis | Operación |
|-------------|----------|-----------|
| LOAD        | `LOAD rd, offset(rs1)` | rd = MEM[rs1+offset] |
| STORE       | `STORE rs2, offset(rs1)` | MEM[rs1+offset] = rs2 |
| LOADI       | `LOADI rd, imm` | rd = imm |

---

## Control de Flujo
| Instrucción | Sintaxis | Operación |
|-------------|----------|-----------|
| JUMP        | `JUMP imm` | PC = imm |
| BEQ         | `BEQ rs1, rs2, imm` | if rs1==rs2 then PC=imm |
| BNE         | `BNE rs1, rs2, imm` | if rs1!=rs2 then PC=imm |
| BLT         | `BLT rs1, rs2, imm` | if rs1<rs2 then PC=imm |

---

## Hash
| Instrucción | Sintaxis | Operación |
|-------------|----------|-----------|
| HASH_INIT   | `HASH_INIT` | Carga IVs (A,B,C,D) desde bóveda |
| HASH_BLOCK  | `HASH_BLOCK rs1` | Procesa bloque de 64 bits |
| HASH_FINAL  | `HASH_FINAL` | Exporta hash final (256 bits) |

---

## Bóveda / Firma
| Instrucción | Sintaxis | Operación |
|-------------|----------|-----------|
| VSTORE      | `VSTORE vault_idx, rs1` | Guarda en bóveda |
| VINIT       | `VINIT` | Inicializa hash desde bóveda |
| SIGN        | `SIGN rd, vault_idx` | Firma hash con llave privada |
| VERIFY      | `VERIFY rd, vault_idx` | Verifica firma |

---

## Especiales
| Instrucción | Sintaxis | Operación |
|-------------|----------|-----------|
| MUL         | `MUL rd, rs1, rs2` | rd = (rs1 * rs2) trunc 64 |
| MOD         | `MOD rd, rs1, rs2` | rd = rs1 mod rs2 |
| MULMOD      | `MULMOD rd, rs1, rs2` | rd = (rs1 * rs2) mod PRIME_MOD |
| ROTL        | `ROTL rd, rs1, imm` | rd = rotl(rs1, imm) |
| ROTR        | `ROTR rd, rs1, imm` | rd = rotr(rs1, imm) |
| NONLIN      | `NONLIN rd, rs1` | rd = rotl(rs1,13) ^ (rs1*GOLDEN_RATIO) |

---

## Constantes
- GOLDEN_RATIO = `0x9e3779b97f4a7c15`  
- PRIME_MOD = `0xFFFFFFFB`  
- IVs: `INITIAL_A..D` (valores de arranque del hash)
