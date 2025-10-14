// Función: toy_mdma_hash_block (R8-R11: Estado, R4-R7: Punteros, R3: Block)

// Carga los valores iniciales desde bodega
HASH_INIT
LOADI R1, 0
LOAD R25, 0(R1) // TRAE de mem el cont de bloques
HASH_BLOCK R3// quita el contador de bloques

// Preparar desplazamientos y máscaras para construir constantes de 64 bits
LOADI R18, 16                // shift de 16 bits
LOADI R19, 48                // shift de 48 bits
LOADI R22, 32                // shift de 32 bits

LOADI R30, -1                // R30 = 0xFFFF_FFFF_FFFF_FFFF
SHIFTR R30, R30, R19         // R30 = 0x0000_0000_0000_FFFF (máscara de 16 bits)

// Construir GOLDEN_RATIO (0x9E37_79B9_7F4A_7C15) en R1 usando segmentos de 16 bits
LOADI R1, 0
LOADI R20, -0x61C9           // segmento alto 0x9E37
AND R20, R20, R30
OR R1, R1, R20
SHIFTL R1, R1, R18

LOADI R20, 0x79B9
AND R20, R20, R30
OR R1, R1, R20
SHIFTL R1, R1, R18

LOADI R20, 0x7F4A
AND R20, R20, R30
OR R1, R1, R20
SHIFTL R1, R1, R18

LOADI R20, 0x7C15
AND R20, R20, R30
OR R1, R1, R20

// Constantes pequeñas directas
LOADI R2, 3                  // R2 = 3
LOADI R13, 5                 // R13 = 5

// Construir PRIME_MOD (0x0000_0000_FFFF_FFFB) en R12
LOADI R12, -1
SHIFTR R12, R12, R22         // R12 = 0x0000_0000_FFFF_FFFF
ADDI R12, R12, -4            // R12 = 0x0000_0000_FFFF_FFFB

// Máscara completa de 64 bits
LOADI R31, -1                // R31 = 0xFFFF_FFFF_FFFF_FFFF


LOADI R27, 1
LOADI R26, 0
etiqueta: 
HASH_BLOCK R3

// 2. Mezcla No Lineal (f, g, h)

CALC_F R15, R8, R9        // R15 = f = (A & B) ^ (A & C)
CALC_G R14, R9, R10       // R14 = g = (B & C) ^ (~B & D)
CALC_H R16, R8, R9        // R16 = h = A ^ B ^ C ^ D


// 3. Paso de Multiplicación-Mezcla
// mul = (block * GOLDEN_RATIO) & 0xFF...FF -> R17 = mul
MUL R17, R3, R1             // R17 = block * GOLDEN_RATIO
AND R17, R17, R31            // Enmascarar a 64 bits

// 4. Actualizaciones de Ronda (A, B, C, D)
UPDATE_A R8, R8, R15, R17, R9
UPDATE_B R9, R9, R14, R3, R10
UPDATE_C R10, R10, R16, R17, R11
UPDATE_D R11, R11, R8, R3, R15


SUB R25, R25, R27
BEQ R25, R26, etiqueta

// Exporta el estado final
hash_final R8


// Firma de documento
SGEN 0, R8, R12

#######################################################################
# Test: Carga de archivo (loader.py) + HASH_INIT/BLOCK/FINAL
# Qué prueba:
#  - Lectura de header y puntero creados por loader.load_file_into_memory
#  - Recorrido de bloques 64-bit y procesamiento con HASH_BLOCK
#  - Exportación del hash final con HASH_FINAL a registros consecutivos
#
# Cómo ejecutar (dos opciones):
#  Opción A: cargar datos en DataMemory desde Python antes de correr el pipeline:
#    from compiler.isa_assembler.loader import load_file_into_memory
#    p = Pipeline(words)  # lista de instrucciones ensambladas de este .s
#    load_file_into_memory(p.data_mem, path="ruta/al/archivo.bin", header_base=0)
#    p.run()  # elige opción "2"
#
#  Opción B: si quieres ver solo los bloques en consola:
#    python -m compiler.isa_assembler.loader  # modo interactivo clásico
#
# Estructura en memoria escrita por loader:
#   - [0x0000]       = count (R24 al cargar)
#   - [0x0008]       = blocks_base (puntero, R21)
#   - [blocks_base]  = block0 (UInt64)
#   - [blocks_base+8]= block1
#   - ...
#
# Resultados esperados al finalizar:
#   - R24 = count total de bloques
#   - R21 = puntero blocks_base
#   - R26 = índice final (== count)
#   - R20..R23 = hash final exportado por HASH_FINAL (Vec4x64 → R20..R23)
#   - Revisa reporte final del pipeline para métricas (mem_accesses, etc.)
#######################################################################

        ############################
        # 0) Leer header y puntero
        ############################
        LOADI   R1, 0                # base del header
        LOAD    R24, 0(R1)           # R24 = count (número de bloques)
        LOAD    R21, 8(R1)           # R21 = blocks_base (puntero a primer bloque)

        ############################
        # 1) Inicializar estado hash
        ############################
        HASH_INIT                     # Carga IVs (desde bóveda o constantes)

        ############################
        # 2) Preparar lazo sobre bloques
        #    idx en R26, shift=3 en R18 para *8
        ############################
        LOADI   R26, 0                # idx = 0
        LOADI   R18, 3                # multiplicador de 8 (<<3)

loop:
        # if (idx == count) -> end
        BEQ     R26, R24, end

        # offset = idx << 3
        SHIFTL  R27, R26, R18         # R27 = idx * 8
        # addr = blocks_base + offset
        ADD     R28, R21, R27         # R28 = dirección del bloque actual

        # Cargar bloque y procesar
        LOAD    R3, 0(R28)            # R3 = block[idx]
        HASH_BLOCK R3                  # Actualiza A,B,C,D internamente (R4..R7)

        # idx++
        ADDI    R26, R26, 1
        JUMP    loop

end:
        ############################
        # 3) Exportar hash final a R20..R23
        ############################
        HASH_FINAL R20                 # Escribe Vec4x64 en R20..R23

        #######################################################################
        # Notas de verificación manual (al terminar la ejecución):
        # - R24 (count) y R21 (blocks_base) deben coincidir con el loader.
        # - R26 debe terminar igual que R24 (todos los bloques procesados).
        # - R20..R23 contienen el hash final (dependiente del archivo cargado).
        # - En el reporte del pipeline:
        #    · Accesos a memoria > 0 (por LOAD de los bloques)
        #    · Accesos a bóveda según HASH_INIT (si leyó IVs de bóveda)
        #    · Sin violaciones si blocks_base evita VAULT_ADDR_RANGE (loader reubica).
        #######################################################################
