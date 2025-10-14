# test_shift.s
# Prueba de las instrucciones SHIFTL, SHIFTR, ROTL y ROTR
# Cobertura: desplazamientos lógicos y rotaciones circulares de 64 bits.

        # --- Inicialización ---
        LOADI  R1,  1           # R1 = 0x0000...0001
        LOADI  R2,  4           # R2 = shift = 4 bits
        LOADI  R3,  32767   # R3 = bit más alto (para probar overflow)
        LOADI  R4,  63          # R4 = shift = 63 bits

        # --- SHIFTL (lógico izquierda) ---
        SHIFTL R5, R1, R2       # R5 = 1 << 4  = 0x10
        SHIFTL R6, R3, R1       # R6 = 0x8000.. << 1 = 0x0 (overflow)
        SHIFTL R7, R1, R4       # R7 = 1 << 63 = 0x8000000000000000

        # --- SHIFTR (lógico derecha) ---
        SHIFTR R8,  R7, R4      # R8 = 0x8000.. >> 63 = 1
        SHIFTR R9,  R7, R2      # R9 = 0x8000.. >> 4 = 0x0800000000000000
        SHIFTR R10, R3, R1      # R10 = 0x8000.. >> 1 = 0x4000000000000000

        # --- ROTL (rotación izquierda) ---
        ROTL   R11, R1,  R2      # R11 = rotl(1,4) = 0x10
        ROTL   R12, R3,  R1      # R12 = rotl(0x8000..,1) = 0x1

        # --- ROTR (rotación derecha) ---
        ROTR   R13, R1,  R1      # R13 = rotr(1,1) = 0x8000000000000000
        ROTR   R14, R3,  R1      # R14 = rotr(0x8000..,1) = 0x4000000000000000

        # --- Resultados esperados ---
        # R5  = 0x0000000000000010
        # R6  = 0x0000000000000000
        # R7  = 0x8000000000000000
        # R8  = 0x0000000000000001
        # R9  = 0x0800000000000000
        # R10 = 0x4000000000000000
        # R11 = 0x0000000000000010
        # R12 = 0x0000000000000001
        # R13 = 0x8000000000000000
        # R14 = 0x4000000000000000
