// Función: toy_mdma_hash_block (R8-R11: Estado, R4-R7: Punteros, R3: Block)

// Carga los valores iniciales desde bodega
HASH_INIT
HASH_BLOCK

// Cargar constantes inmutables
LOADI R1, GOLDEN_RATIO 
LOADI R2, 3                 // R2 = 3
LOADI R12, PRIME_MOD         // R12 = PRIME_MOD
LOADI R13, 5                 // R13 = 5
LOADI R31, 0xFFFFFFFFFFFFFFFF // R31 = MÁSCARA CONSTANTE (0xFF...FF)

// 2. Mezcla No Lineal (f, g, h)

CALC_F R15        // R15 = f = (A & B) ^ (A & C)
CALC_G R14        // R14 = g = (B & C) ^ (~B & D)
CALC_H R16        // R16 = h = A ^ B ^ C ^ D


// 3. Paso de Multiplicación-Mezcla
// mul = (block * GOLDEN_RATIO) & 0xFF...FF -> R17 = mul
MUL R17, R3, R1             // R17 = block * GOLDEN_RATIO
AND R17, R17, R31            // Enmascarar a 64 bits

// 4. Actualizaciones de Ronda (A, B, C, D)
UPDATE_A R4 
UPDATE_B R5
UPDATE_C R6
UPDATE_D R7


// Exporta el estado final

hash_final
