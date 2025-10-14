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

El procesador está organizado en cinco etapas de pipeline: Fetch, Decode, Execute, Memory, Writeback. El banco de registros de 32 × 64 bits interactúa con las unidades de memoria y vault por medio de la unidad de control. La bóveda es accesible sólo por instrucciones especiales. El diagrama de bloques muestra las conexiones que existen entre los módulos principales.

### 2.1 Diagrama de bloques y componentes

![Diagrama de Bloques](https://raw.githubusercontent.com/yen31b/images-yen/main/diagbloques.jpg)


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

El modelo se implementa en Python. Cada etapa del pipeline es una clase/archivo (fetch_stage.py, decode_stage.py, ...). El banco de registros se modela como una lista, la bóveda como una clase protegida, la memoria como un diccionario. Las instrucciones se procesan pasando objetos entre funciones, simulando el ciclo real del hardware.

#### Componentes principales del modelo

- **Banco de registros:**  
  Implementado como una estructura (por ejemplo, lista o diccionario) de 32 registros de 64 bits de ancho. Permite almacenar operandos y resultados de las instrucciones ejecutadas. El acceso y modificación de los registros se realiza a través de las etapas del pipeline.

- **Memoria de instrucciones y memoria de datos:**  
  La memoria de instrucciones almacena el programa ensamblado; la memoria de datos guarda los valores intermedios, buffers y resultados. Ambas están modeladas como listas o diccionarios en Python, y son accedidas en las etapas de Fetch y Memory.

- **Bóveda segura (Vault):**  
  Es un componente fundamental para las operaciones de seguridad. Modelada como una clase dedicada, la bóveda almacena llaves privadas e IVs de forma protegida. Solo puede ser accedida por instrucciones especiales, y nunca permite que las llaves sean volcadas a registros generales o memoria convencional.

- **Unidades funcionales:**  
  Incluyen la ALU (Unidad Aritmético-Lógica) para operaciones convencionales y una unidad criptográfica (implementada dentro de la etapa Execute o como clase aparte) para cálculos de hash y firma digital.

#### Pipeline y ciclo de ejecución

El modelo sigue el flujo clásico de instrucciones en cinco etapas, cada una implementada en archivos separados:

1. **Fetch (`fetch_stage.py`)**  
   Recupera la instrucción de la memoria de instrucciones utilizando el Program Counter (PC).

2. **Decode (`decode_stage.py`)**  
   Decodifica la instrucción y determina el tipo, los registros involucrados y las señales de control necesarias para el ciclo.

3. **Execute (`execute_stage.py`)**  
   Realiza la operación aritmética, lógica, de hash o firma digital correspondiente. Si la instrucción requiere acceso a la bóveda, se activa la lógica especial y se delega la operación a la clase de bóveda.

4. **Memory (`memory_stage.py`)**  
   Accede a la memoria de datos para operaciones de carga/almacenamiento, y gestiona la comunicación segura con la bóveda según las restricciones definidas.

5. **Writeback (`writeback_stage.py`)**  
   Escribe el resultado final en el banco de registros, completando el ciclo de la instrucción.

El **archivo `pipeline.py`** coordina el paso de las instrucciones y datos entre etapas, gestionando los buffers y sincronización. El ciclo se repite para cada instrucción hasta alcanzar una instrucción de parada (`HALT`).

#### Manejo de instrucciones especiales

Las instrucciones relacionadas con operaciones criptográficas (hash, firma digital, acceso a bóveda) son identificadas en las etapas de Decode y Execute, activando rutas de control especializadas. Esto asegura que los datos sensibles nunca se expongan fuera de los componentes protegidos, cumpliendo las políticas de seguridad requeridas por la arquitectura.

#### Ejemplo de flujo de ejecución

Un ciclo típico para una instrucción de firma digital sería:

- **Fetch:** Se recupera la instrucción `SIGN`.
- **Decode:** Se identifica como instrucción especial, activando los flags correspondientes.
- **Execute:** Se delega el cálculo al módulo criptográfico, accediendo la bóveda para obtener la llave privada de forma protegida.
- **Memory:** Se almacena la firma en memoria de datos, validando que no se exponga la llave.
- **Writeback:** Se actualizan los registros con el resultado, si corresponde.


---



