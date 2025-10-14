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

// --- Inicializar slot de bóveda con una llave (evitar violaciones por slot no inicializado)
// usamos R4 (valor cargado por HASH_INIT) como llave de ejemplo
VINIT   0,   R4        # Inicializa slot 0 con clave en R4 (autorizado)

// Firma de documento
SGEN    0,   R8,   R12        # slot, state_reg, dst_reg  -> firma escrita en R12..R15

// Verificacion
VERIFY  0,   R12,  R31       # slot, signature_reg, dst_reg  -> resultado (0/1) en R31
