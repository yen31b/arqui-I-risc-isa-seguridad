// Función: toy_mdma_hash_block (R1-R4: Estado, R5-R8: Punteros, R9: Block)

// 1. Carga de Estado y Constantes
LOAD R1, R5          // R1 = A
LOAD R2, R6          // R2 = B
LOAD R3, R7          // R3 = C
LOAD R4, R8          // R4 = D

// Cargar constantes inmutables
LOADI R10, 0x9E3779B97F4A7C15 // R10 = GOLDEN_RATIO
LOADI R11, 3                 // R11 = 3
LOADI R12, 0xFFFFFFFB         // R12 = PRIME_MOD
LOADI R13, 5                 // R13 = 5
LOADI R31, 0xFFFFFFFFFFFFFFFF // R31 = MÁSCARA CONSTANTE (0xFF...FF)

// 2. Mezcla No Lineal (f, g, h)

// Calcular f = (A & B) | (~A & C) -> R15 = f
AND R15, R1, R2              // R15 = A & B
XOR R18, R1, R31             // R18 = ~A
AND R19, R18, R3             // R19 = ~A & C
OR R15, R15, R19             // R15 = f

// Calcular g = (B & C) | (~B & D) -> R14 = g
AND R14, R2, R3              // R14 = B & C
XOR R18, R2, R31             // R18 = ~B
AND R19, R18, R4             // R19 = ~B & D
OR R14, R14, R19             // R14 = g

// Calcular h = A ^ B ^ C ^ D -> R16 = h
XOR R16, R1, R2              // R16 = A ^ B
XOR R16, R16, R3             // R16 = A ^ B ^ C
XOR R16, R16, R4             // R16 = h

// 3. Paso de Multiplicación-Mezcla
// mul = (block * GOLDEN_RATIO) & 0xFF...FF -> R17 = mul
MUL R17, R9, R10             // R17 = block * GOLDEN_RATIO
AND R17, R17, R31            // Enmascarar a 64 bits

// 4. Actualizaciones de Ronda (A, B, C, D)

// A = rol64(A + f + mul, 7) + B
ADD R18, R1, R15             // R18 = A + f
ADD R18, R18, R17            // R18 = A + f + mul
ROTL R18, R18, 7             // Rotación (rol64)
ADD R1, R18, R2              // R1 = A_nuevo

// B = rol64(B + g + block, 11) + (C * 3)
MUL R19, R3, R11             // R19 = C * 3 (R11=3)
ADD R18, R2, R14             // R18 = B + g
ADD R18, R18, R9             // R18 = B + g + block (R9=block)
ROTL R18, R18, 11            // Rotación (rol64)
ADD R2, R18, R19             // R2 = B_nuevo

// C = rol64(C + h + mul, 17) + (D % PRIME_MOD)
MOD R19, R4, R12             // R19 = D % PRIME_MOD (R12=0xFFFFFFFB)
ADD R18, R3, R16             // R18 = C + h
ADD R18, R18, R17            // R18 = C + h + mul
ROTL R18, R18, 17            // Rotación (rol64)
ADD R3, R18, R19             // R3 = C_nuevo

// D = rol64(D + A + block, 19) ^ (f * 5)
MUL R19, R15, R13            // R19 = f * 5 (R15=f, R13=5)
ADD R18, R4, R1              // R18 = D + A_nuevo (¡R1 ya es A_nuevo!)
ADD R18, R18, R9             // R18 = D + A + block
ROTL R18, R18, 19            // Rotación (rol64)
XOR R4, R18, R19             // R4 = D_nuevo

// 5. Almacenamiento de Estado
STORE R1, R5                 // *a = A_nuevo
STORE R2, R6                 // *b = B_nuevo
STORE R3, R7                 // *c = C_nuevo
STORE R4, R8                 // *d = D_nuevo
