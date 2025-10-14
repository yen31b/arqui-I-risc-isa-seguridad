## Probar el flujo completo con `tests/test_loader.py`

Para probar el flujo completo del programa, se utiliza el script de test_loader.py.

1. Se puede ejecutar con el Run desde el editor de codigo, o bien desde terminal con el comando del  `python -m tests.test_loader`.
2. Se selecciona el archivo binario para firmar. El loader lo convierte a bloques de 64 bits, aplica padding y reubica los datos para no invadir `VAULT_ADDR_RANGE`.
3. El script registra la boot image resultante (`set_boot_image`) y crea un `Pipeline` ensamblando `Assembly\hast.s`. Si falta ese archivo, el test se detiene.
4. Elige modo normal o debug. En modo debug puedes inspeccionar memoria (bloques, hash, firma) y registros en cada paso del pipeline.
5. Al finalizar se genera un archivo firmado junto al original (`<nombre>.signed.<ext>`), además de un dump hexadecimal de apoyo. También imprime el hash y la firma cargados en memoria y corre `VERIFY` dentro de la bóveda (slot 0) para confirmar que la firma coincide.


---
## Cobertura de pruebas por cada módulo

Cada bloque del proyecto tiene pruebas para verificar la funcionalidad por separado de cada modulo.

- `compiler/isa_assembler`: ver `compiler/tests/test_*.py` para validar parsing, generación de hex y ensamblado.
- `isa`: las definiciones en `isa/` se ejercitan desde los tests del ensamblador y cualquier cambio debe acompañarse con un nuevo `test_*.py` en `compiler/tests`.
- `pipeline`: el flujo completo se verifica con `tests/test_loader.py`, que levanta el pipeline con la boot image generada por el loader.
- Utilidades adicionales: `tests/test_loader_beta.py` cubre escenarios alternativos del loader e integra memoria y bóveda.


# Prueba de solamente el compilador para Ensamblador de ISA definido

`compiler/isa_assembler` es el archivo que realiza la lectura del archivo ASM, compila usando la definición de ISA (`isa/`). 

Para ensamblar un programa se puede hacer por estos comandos:

```Comandos para compilar 

python -m compiler.isa_assembler.cli ruta\al\programa.asm -f hex --emit-address

Para compilar y generar el .txt:

python -m compiler.isa_assembler.cli ruta\al\programa.asm --format hex -o programa.txt

```

La herramienta entiende etiquetas, saltos, modos de direccionamiento y
operaciones especiales (bóveda, hash) usando los valores declarados en
`isa_definition.py`. El comando de ayuda `python -m compiler.isa_assembler.cli -h`
describe las opciones disponibles.

---


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
- **V-TYPE**: `opcode (6) | vault_idx (5) | rs1 (5) | funct (16)`  # para instrucciones de bóveda
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

## 📌 Instrucciones de bóveda (Vault Instructions)

> Fuente única de verdad: `VAULT_INSTR_NAMES` en isa/isa_definition.py debe contener exactamente estos nombres.

| Instrucción | Sintaxis | Descripción |
|-------------|----------|-------------|
| **KVW / VSTORE** | `KVW vault_idx, rs1` | Escribe un valor de 64 bits en el slot de la bóveda. (acepta también `VSTORE`) |
| **KVL / VLOAD**  | `KVL rd, vault_idx` | Lee un valor de 64 bits desde la bóveda (devuelve UInt64). (sin exponer llaves a memoria) |
| **VINIT**        | `VINIT vault_idx, rs1` | Inicializa un slot de bóveda (bootstrap), semántica similar a KVW |
| **KVOP**         | `KVOP vault_idx, rs1, funct` | Opera sobre el slot usando función interna de bóveda; resultado controlado por VaultInterface |
| **SGEN / SIGN**  | `SGEN slot, state_reg [, dst_reg]` | Genera firma digital usando la llave privada del slot y el estado hash (A,B,C,D). Si se especifica dst_reg, la firma (4×UInt64) se escribe en `dst_reg..dst_reg+3`. |
| **VERIFY**       | `VERIFY slot, signature_reg [, dst_reg]` | Verifica firma dentro de la bóveda; devuelve flag/booleano en `dst_reg` (o como resultado si no se especifica dst_reg). |
| **VLOAD**        | `VLOAD rd, vault_idx` | Sinónimo/alias de `KVL` (si se usa en el ISA mantener coherencia en decode). |

🔒 **Políticas de seguridad y restricciones**:
- Llaves privadas en bóveda **nunca deben aparecer** en memoria o registros generales.  
- `DataMemory.validate_memory_access` debe lanzar `PermissionError` si la dirección está en `VAULT_ADDR_RANGE`.  
- Solo instrucciones en `VAULT_INSTR_NAMES` pueden acceder a la bóveda.  
- `VaultInterface` centraliza operaciones; si no está instanciada y se solicita la bóveda → `RuntimeError`.  
- `require_authorization_for_write = True` (configurable) → escrituras a bóveda deben validar autorización.  
- `protect_slots_from_memory = True` → prohibir cualquier STORE que intente escribir el contenido de un slot en DataMemory.

📊 **Latencias orientativas**
| Operación | Ciclos |
|------------|---------|
| KVW / VSTORE / VINIT | 5 |
| KVL / VLOAD | 3 |
| KVOP | 6 |
| SGEN / SIGN | 8 |
| VERIFY | 6–8 |

---

## 📌 Instrucciones de hash

| Instrucción | Sintaxis | Descripción |
|-------------|----------|-------------|
| **HASH_INIT**  | `HASH_INIT` | Carga IVs (A,B,C,D) desde la bóveda (o desde slots iniciales). |
| **HASH_BLOCK** | `HASH_BLOCK rs1` | Procesa bloque de 64 bits en `rs1` (usar hash_accel.apply_block). |
| **HASH_FINAL** | `HASH_FINAL rd` | Exporta hash final (256 bits) al lugar definido (rd..rd+3 o buffer en memoria segura). |

- Convención para estado hash: `Vec4x64` (A,B,C,D). En WB mapear a `rd, rd+1, rd+2, rd+3` o usar registro/vector opaco según diseño.

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
| **UPDATE_A** | `UPDATE_A rd, rs1, rs2, rs3, rs4` | `rd = rol64(rs1 + rs2 + rs3, 7) + rs4` |
| **UPDATE_B** | `UPDATE_B rd, rs1, rs2, rs3, rs4` | `rd = rol64(rs1 + rs2 + rs3, 11) + (rs4 * 3)` |
| **UPDATE_C** | `UPDATE_C rd, rs1, rs2, rs3, rs4` | `rd = rol64(rs1 + rs2 + rs3, 17) + (rs4 % PRIME_MOD)` |
| **UPDATE_D** | `UPDATE_D rd, rs1, rs2, rs3, rs4` | `rd = rol64(rs1 + rs2 + rs3, 19) ^ (rs4 * 5)` |

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

1. `HASH_INIT` → carga IVs desde la bóveda (o slots IV).  
2. Repetir `HASH_BLOCK` por cada bloque de 64 bits del archivo.  
3. `HASH_FINAL` → obtiene hash (A,B,C,D) como `Vec4x64`.  
4. `SGEN / SIGN` → combinación hash + llave privada dentro de la bóveda.  
5. Guardar archivo + firma (firma debe escribirse en archivo, pero la llave nunca debe salir de la bóveda).  
6. `VERIFY` → recalcula hash y compara con firma dentro de bóveda.

---

## 📌 Tipos y contratos globales de seguridad

| Tipo | Descripción |
|------|--------------|
| **UInt64** | Entero sin signo de 64 bits |
| **Vec4x64** | Estado hash de 4 × UInt64 (A,B,C,D) |
| **Firma** | Tupla `(UInt64 × 4)` |

**VAULT_ADDR_RANGE** = `(0x1000, 0x1FFF)`  → valor canónico, usado por DataMemory.validate_memory_access  
**VAULT_INSTR_NAMES** = `{KVW, VSTORE, KVL, VLOAD, VINIT, KVOP, SGEN, SIGN, VERIFY}`

---

## 📌 Políticas de seguridad (enfáticas)

- Las llaves privadas no pueden volcarse a memoria ni escribirse en registros general-purpose.  
  - Enforcement: DataMemory.validate_memory_access lanza `PermissionError` para lecturas/escrituras en `VAULT_ADDR_RANGE`.  
  - WriteBackStage debe verificar `control_signals` y bloquear cualquier intento de escribir una llave privada fuera de la bóveda.  
- Todos los accesos a datos de bóveda se deben hacer únicamente vía `VaultInterface`.  
- `MemoryStage` para instrucciones con `control_signals['use_boveda'] == True` delega a `VaultInterface` y NO usa `DataMemory`.  
- `MemoryStage` debe devolver en su salida `vault_accessed: True/False` explícito.  
- `VaultInterface` debe exponer `get_security_report()` con métricas (ops por tipo, fallas, autorizaciones).

---

## 📌 Retornos esperados

| Instrucción | Retorno |
|-------------|----------|
| KVW / VSTORE / VINIT | None |
| KVL / VLOAD | UInt64 |
| KVOP | UInt64 |
| SGEN / SIGN | Tuple(UInt64 × 4) |
| VERIFY | Boolean / UInt64 flag |

---

## 📌 Pipeline y comportamiento

| Etapa | Descripción |
|--------|-------------|
| **ID (Decode)** | Marca `control_signals['use_boveda'] = True` si la instrucción está en `VAULT_INSTR_NAMES`. |
| **EX (Execute)** | Preparar argumentos (slot_idx, state, value). Si `use_boveda`: no volcar claves a registros; propagar `vault_signal` y/o delegar a `VaultInterface`. |
| **MEM (Memory)** | Si `use_boveda`: delega a `VaultInterface` (no usar DataMemory). `DataMemory` bloqueará accesos directos a `VAULT_ADDR_RANGE`. Devuelve `vault_accessed=True`. |
| **WB (WriteBack)** | Escribe solo resultados permitidos por la política. Para `Vec4x64`/firma decidir convención (ej. `rd..rd+3`). Bloquear volcado de claves a memoria. |

---

## 📌 Pruebas exigidas (mínimo, y comportamiento estricto)

- KVW/VSTORE/VINIT: múltiples escrituras a distintos slots → comprobar `VaultInterface.slots` y que `DataMemory.memory` NO cambió; `DataMemory.metrics['mem_accesses']` no incrementa por estas operaciones.  
- KVL/VLOAD: lecturas retornan `UInt64` correctos (tipado estricto).  
- KVOP: comportamiento determinista según `VaultInterface` de prueba.  
- SGEN/SIGN: aceptar varios formatos de `hash_state` (dict/tuple/list) → devolver 4×`UInt64` (firma).  
- LOAD/STORE: accesos dentro de `VAULT_ADDR_RANGE` deben lanzar `PermissionError` en `DataMemory`.  
- Propagación: instrucciones ALU/no-mem propagan `result` de EX → MEM → WB sin modificación.  
- Configuración: si `vault_if is None` y `use_boveda == True` → `RuntimeError`.  
- `MemoryStage` debe devolver `vault_accessed` explícito y `DataMemory` debe incrementar `security_blocks` cuando bloquea accesos.



