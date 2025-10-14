# Proyecto Grupal ISA para Seguridad de la Información
## Documento de Diseño


## 1. Arquitectura del Set de Instrucciones

La arquitectura está basada en un ISA tipo RISC, fue diseñada para implementar una aplicacion de seguridad, como lo es la firma digital y verificación de integridad.

### 1.1 Modos de direccionamiento

- **Inmediato:** Carga de valores constantes en registros.
- **Directo:** Para acceso a memoria usando etiquetas o direcciones absolutas.
- **Indirecto:** El acceso a memoria se realiza usando el contenido de un registro como dirección base.
- **Modo especial para la bóveda:** El acceso a la bóveda se realiza únicamente mediante instrucciones tipo VAULT.

### 1.2 Tipos y tamaños de datos

- **Registros:** 32 registros generales de 64 bits (`R0`–`R31`).
- **Datos:** Operaciones sobre palabras de 64 bits.
- **Bóveda:** Slots de 64 bits para las llaves privadas.
- **Especiales:** Vec4x64 para el estado de hash (A,B,C,D).

### 1.3 Sintaxis y codificación de instrucciones

- **R-TYPE:** `opcode (6) | rd (5) | rs1 (5) | rs2 (5) | funct (11)`
- **I-TYPE:** `opcode (6) | rd (5) | rs1 (5) | imm (16)`
- **S-TYPE:** `opcode (6) | rs1 (5) | rs2 (5) | imm (16)`
- **V-TYPE:** `opcode (6) | vault_idx (5) | rs1 (5) | funct (16)`
- **H-TYPE:** `opcode (6) | rs1 (5) | funct (21)`

### 1.4 Registros disponibles y de propósito general

- **R0:** Constante 0.
- **R1–R28:** Uso general.
- **SP (R29):** Stack Pointer.
- **FP (R30):** Frame Pointer.
- **RA (R31):** Return Address.
- **PC, SR:** Especiales de la microarquitectura como PC y status register.

### 1.5 Justificación de diseño

- **32 registros y 64 bits:** Permiten paralelismo y eficiencia en las operaciones de codificación, para ToyMDMA y el almacenamiento seguro.
- **Formatos de instrucción:** Mantienen simplicidad en el decodificador y flexibilidad para crear instrucciones especializadas.
- **Vault:** La implementación de una bóveda permite que se cumplan los requisitos de seguridad, ya que de este modo se protegen las llaves privadas de accesos no autorizados.
- **Instrucciones especiales:** Permiten que exista menor latencia en el hash y firma, lo cual optimiza los ciclos en la simulación del hardware.

### 1.6 Green Card

Se puede acceder en [`docs/green_card.md`](./green_card.md)

---

## 2. Organización / Microarquitectura

### 2.1 Diagrama de bloques y componentes

![Diagrama de Bloques]((https://raw.githubusercontent.com/yen31b/images-yen/refs/heads/main/diagbloques.jpg))

**Componentes principales:**
- **Fetch Stage:** Recupera la instrucción de la memoria de instrucciones utilizando el Program Counter (PC).
- **Decode Stage:** Decodifica la instrucción, identifica el tipo y determina los registros/operandos involucrados.
- **Execute Stage:** Realiza operaciones aritméticas, lógicas y de control de flujo, incluyendo instrucciones especializadas de hash/firma.
- **Memory Stage:** Accede a la memoria de datos para lecturas/escrituras y gestiona el acceso seguro a la bóveda.
- **Writeback Stage:** Escribe los resultados en el banco de registros.
- **Banco de Registros:** 32 registros generales de 64 bits.
- **Vault:** almacenamiento protegido para las llaves privadas.
- **Memoria de Instrucciones y Memoria de Datos:** Almacenan el código y los datos operativos del procesador.


### 2.2 Flujo de datos e instrucciones

- El ciclo inicia con **fetch** desde memoria de instrucciones.
- La **unidad de control** decodifica la instrucción y activa la ruta de datos adecuada.
- Operaciones regulares se realizan usan ALU y banco de registros.
- Instrucciones de bóveda pasan por la Interfaz de la bóveda, en esta fase nunca se exponen llaves a memoria o registros generales.
- Operaciones de hash/firma utilizan la el hash y acceden a la llave de la bóveda.

---

## 3. Modelado del software

### 3.1 Implementación del modelo de procesador

- **Banco de registros:** Array de 32 elementos de 64 bits.
- **Unidades funcionales:** Métodos para cada operación básica y especializada.
- **Bóveda:** Instancia de la `VaultInterface`, slots internos y acceso con control.
- **Memoria:** Arrays para instrucciones y datos, inicialización desde archivos hex generados por el ensamblador.
- **Ciclo de ejecución:** `fetch → decode → execute → memory → writeback`.

### 3.2 Manejo de instrucciones y ciclo de ejecución



---



