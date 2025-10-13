# test2.s (Shift con registros)
# Usamos R18 para los valores de desplazamiento

        ################################################################
        # 1) Construir 0x0001000200010002 en R1 (segmentos pequeños)
        ################################################################
        LOADI   R1,   0x0001
        LOADI   R18,  16
        SHIFTL  R1,   R1,    R18        # R1 = R1 << 16
        LOADI   R17,  0x0002
        OR      R1,   R1,    R17        # R1 = 0x00010002

        LOADI   R18,  32
        SHIFTL  R1,   R1,    R18        # R1 = R1 << 32
        LOADI   R17,  0x0001
        OR      R1,   R1,    R17

        LOADI   R18,  48
        SHIFTL  R1,   R1,    R18        # R1 = R1 << 48
        LOADI   R17,  0x0002
        OR      R1,   R1,    R17        # R1 = 0x0001000200010002

        ################################################################
        # 2) Construir 0x0003000400050006 en R2 (segmentos pequeños)
        ################################################################
        LOADI   R2,   0x0003
        LOADI   R18,  16
        SHIFTL  R2,   R2,    R18
        LOADI   R17,  0x0004
        OR      R2,   R2,    R17

        LOADI   R18,  32
        SHIFTL  R2,   R2,    R18
        LOADI   R17,  0x0005
        OR      R2,   R2,    R17

        LOADI   R18,  48
        SHIFTL  R2,   R2,    R18
        LOADI   R17,  0x0006
        OR      R2,   R2,    R17        # R2 = 0x0003000400050006

        ################################################################
        # 3) Construir 0x000A000B000C000D en R3 (segmentos pequeños)
        ################################################################
        LOADI   R3,   0x000A
        LOADI   R18,  16
        SHIFTL  R3,   R3,    R18
        LOADI   R17,  0x000B
        OR      R3,   R3,    R17

        LOADI   R18,  32
        SHIFTL  R3,   R3,    R18
        LOADI   R17,  0x000C
        OR      R3,   R3,    R17

        LOADI   R18,  48
        SHIFTL  R3,   R3,    R18
        LOADI   R17,  0x000D
        OR      R3,   R3,    R17        # R3 = 0x000A000B000C000D

        ################################################################
        # 4) Operaciones de bóveda y firma
        ################################################################
        VINIT    0,    R1               # Inicializa slot 0 con clave en R1
        KVW      0,    R2               # Slot 0 ← valor en R2
        VSTORE   1,    R3               # Slot 1 ← valor en R3

        KVL      R4,    0               # R4 ← Slot 0
        VLOAD    R5,    1               # R5 ← Slot 1

        LOADI    R6,    42              # Parámetro para KVOP
        KVOP     0,    R6,    1         # Slot 0 ← vault_op(slot0,42,funct=1)

        # Preparar estado hash en R7–R10
        LOADI    R7,    1
        LOADI    R8,    2
        LOADI    R9,    3
        LOADI    R10,   4

        SGEN     R11,   0,    R7        # Firma (R11–R14) con slot 0
        VERIFY   R15,   0,    R11       # R15 = 1 si verificación correcta

        VLOAD    R16,   0               # R16 ← Slot 0 tras KVOP
