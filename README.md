# 🟩 Instruction Reference Sheet (Green Card)

## 📌 Registros
- **32 registros generales de 64 bits**: `R0`–`R31`
- **R0**: siempre 0 (convención)
- **SP (R29)**: Stack Pointer  
- **FP (R30)**: Frame Pointer  
- **RA (R31)**: Return Address  
- **PC, SR**: registros especiales (Program Counter, Status Register)

---

## 📌 Formatos de instrucción (32 bits)

- **R-TYPE**: `opcode (6) | rd (5) | rs1 (5) | rs2 (5) | funct (11)`
- **I-TYPE**: `opcode (6) | rd (5) | rs1 (5) | imm (16)`
- **S-TYPE**: `opcode (6) | rs1 (5) | rs2 (5) | imm (16)`
- **V-TYPE**: `opcode (6) | vault_idx (5) | rs1 (5) | funct (16)`
- **H-TYPE**: `opcode (6) | rs1 (5) | funct (21)`

---

## 📌 Instrucciones principales

| Instrucción | Formato | Sintaxis | Descripción |
|-------------|---------|----------|-------------|
| **ADD**     | R | `ADD rd, rs1, rs2` | Suma: `rd = rs1 + rs2` |
| **SUB**     | R | `SUB rd, rs1, rs2` | Resta |
| **XOR**     | R | `XOR rd, rs1, rs2` | XOR bit a bit |
| **ADDI**    | I | `ADDI rd, rs1, imm` | Suma inmediata |
| **LOAD**    | I | `LOAD rd, offset(rs1)` | Carga desde memoria |
| **STORE**   | S | `STORE rs2, offset(rs1)` | Guarda en memoria |
| **LOADI**   | I | `LOADI rd, imm` | Carga inmediato largo (constantes) |
| **JUMP**    | I | `JUMP imm` | Salto incondicional |
| **BEQ**     | I | `BEQ rs1, rs2, imm` | Salto si igual |
| **BNE**     | I | `BNE rs1, rs2, imm` | Salto si distinto |

---

## 📌 Instrucciones de bóveda

| Instrucción | Sintaxis | Descripción |
|-------------|----------|-------------|
| **VSTORE**  | `VSTORE vault_idx, rs1` | Guarda valor en bóveda |
| **VINIT**   | `VINIT` | Inicializa valores de hash (A,B,C,D) desde bóveda |
| **SIGN**    | `SIGN rd, vault_idx` | Firma hash con llave privada en bóveda |
| **VERIFY**  | `VERIFY rd, vault_idx` | Verifica firma usando llave en bóveda |

🔒 **Reglas de seguridad**:
- La bóveda no se puede leer como memoria normal.  
- Llaves privadas nunca salen a registros ni memoria.  
- Solo `SIGN` y `VERIFY` acceden a llaves.

---

## 📌 Instrucciones de hash

| Instrucción | Sintaxis | Descripción |
|-------------|----------|-------------|
| **HASH_INIT**  | `HASH_INIT` | Carga IVs (A,B,C,D) desde bóveda |
| **HASH_BLOCK** | `HASH_BLOCK rs1` | Procesa bloque de 64 bits en `rs1` |
| **HASH_FINAL** | `HASH_FINAL` | Exporta hash final (256 bits) a memoria |

---

## 📌 Instrucciones especiales

| Instrucción | Sintaxis | Descripción |
|-------------|----------|-------------|
| **MUL**     | `MUL rd, rs1, rs2` | Multiplicación truncada a 64 bits |
| **MOD**     | `MOD rd, rs1, rs2` | Reducción modular |
| **MULMOD**  | `MULMOD rd, rs1, rs2` | `(rs1 * rs2) mod PRIME_MOD` |
| **ROTL**    | `ROTL rd, rs1, imm` | Rotación izquierda |
| **ROTR**    | `ROTR rd, rs1, imm` | Rotación derecha |
| **NONLIN**  | `NONLIN rd, rs1` | Función no lineal: `rotl(x,13) XOR (x*GOLDEN_RATIO)` |
| **CALC_F**  | `CALC_F rd, rs1, rs2` | `(rs1 & rs2) ^ (rs1 & C)` donde `C = R10` |
| **CALC_G**  | `CALC_G rd, rs1, rs2` | `(rs1 & rs2) ^ (~rs1 & D)` donde `D = R11` |
| **CALC_H**  | `CALC_H rd, rs1, rs2` | `rs1 ^ rs2 ^ C ^ D` donde `C = R10`, `D = R11` |
| **UPDATE_A** | `UPDATE_A rd, rs1, rs2, rs3, rs4` | `rd = rol64(rs1 + rs2 + rs3, 7) + rs4`<br>→ A = rol64(A + f + mul, 7) + B |
| **UPDATE_B** | `UPDATE_B rd, rs1, rs2, rs3, rs4` | `rd = rol64(rs1 + rs2 + rs3, 11) + (rs4 * 3)`<br>→ B = rol64(B + g + block, 11) + (C * 3) |
| **UPDATE_C** | `UPDATE_C rd, rs1, rs2, rs3, rs4` | `rd = rol64(rs1 + rs2 + rs3, 17) + (rs4 % PRIME_MOD)`<br>→ C = rol64(C + h + mul, 17) + (D % PRIME_MOD) |
| **UPDATE_D** | `UPDATE_D rd, rs1, rs2, rs3, rs4` | `rd = rol64(rs1 + rs2 + rs3, 19) ^ (rs4 * 5)`<br>→ D = rol64(D + A + block, 19) ^ (f * 5) |


---

## 📌 Constantes ToyMDMA

- **GOLDEN_RATIO** = `0x9e3779b97f4a7c15`  
- **PRIME_MOD** = `0xFFFFFFFB`  
- **INITIAL_A** = `0x6A09E667F3BCC908`  
- **INITIAL_B** = `0xBB67AE8584CAA73B`  
- **INITIAL_C** = `0x3C6EF372FE94F82B`  
- **INITIAL_D** = `0xA54FF53A5F1D36F1`

---

## 📌 Flujo típico de firma digital

1. `HASH_INIT` → carga IVs desde bóveda.  
2. `HASH_BLOCK` → procesa bloques de archivo.  
3. `HASH_FINAL` → obtiene hash (A,B,C,D).  
4. `SIGN` → combina hash con llave privada de bóveda.  
5. Guardar archivo + firma.  
6. `VERIFY` → recalcula hash y compara con firma.

---
