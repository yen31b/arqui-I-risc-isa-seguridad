# test2.s - Pruebas de BÓVEDA (casos válidos e inválidos)
# Objetivo: verificar VINIT, KVW, KVL/VLOAD, KVOP, SGEN, VERIFY y violaciones (slot no inicializado, acceso a rango de bóveda por STORE).
# Al ejecutar el programa en pipeline.run() usar la opción "2" para ejecutar hasta el final
# y revisar el reporte final (registros y métricas de bóveda).

        ############################
        # Preparación: construir valores 64-bit en R1..R3
        ############################
        LOADI   R1,   0x0001
        LOADI   R18,  16
        SHIFTL  R1,   R1,    R18
        LOADI   R17,  0x0002
        OR      R1,   R1,    R17
        LOADI   R18,  32
        SHIFTL  R1,   R1,    R18
        LOADI   R17,  0x0001
        OR      R1,   R1,    R17
        LOADI   R18,  48
        SHIFTL  R1,   R1,    R18
        LOADI   R17,  0x0002
        OR      R1,   R1,    R17        # R1 = key candidate

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
        OR      R2,   R2,    R17        # R2 = value payload

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
        OR      R3,   R3,    R17        # R3 = other payload

        ################################################################
        # 1) Operaciones válidas:
        #    - Inicializar slot 2 con clave (VINIT)
        #    - Escribir slot 2 con KVW
        #    - Leer slot 2 con VLOAD -> R4 (debe igual a R2)
        ################################################################
        VINIT   2,    R1           # Inicializa slot 2 con clave en R1 (autorizado)
        KVW     2,    R2           # Slot 2 ← valor en R2 (autorizado)
        VLOAD   2,    R4           # R4 ← Slot 2 (debe ser igual a R2)

        ################################################################
        # 2) Violación: leer slot no inicializado (slot 3) -> debe contabilizar violación
        #    - KVL 3, R5  (slot 3 no fue inicializado previamente)
        #    Esperado: VaultInterface/KeyVault levantan VaultAccessError y se contabiliza violación.
        ################################################################
        KVL     3,    R5           # INTENCIONAL: slot 3 no inicializado -> violación esperada

        ################################################################
        # 3) Firma y verificación:
        #    - Preparar estado hash en R7..R10 (valores de prueba)
        #    - SGEN produce firma escrita en R11..R14 (dst = R11)
        #    - VERIFY comprueba firma desde R11 (dst flag en R15)
        ################################################################
        LOADI   R7,    1
        LOADI   R8,    2
        LOADI   R9,    3
        LOADI   R10,   4

        SGEN    2,    R7,   R11   # slot=2, state_reg=R7, dst=R11 -> firma en R11..R14
        VERIFY  2,    R11,  R15   # slot=2, signature_reg=R11, dst=R15 (1 == OK)

        ################################################################
        # 4) KVOP: operación sobre slot (comprobar que no rompe el slot)
        #    - Preparamos R6 con parámetro y llamamos KVOP 2, R6, 1
        ################################################################
        LOADI   R6,    42
        KVOP    2,    R6,    1    # operación controlada sobre slot 2 (side-effect según VaultInterface)

        ################################################################
        # 5) Leer slot 2 final y copiar a R16 para inspección
        ################################################################
        VLOAD   2,    R16         # R16 ← Slot 2 (valor tras KVOP si cambia)

        ################################################################
        # 6) Intento de acceso ilegal a rango de bóveda mediante STORE
        #    - Esto debe ser bloqueado por DataMemory.validate_memory_access
        #    - Dirección elegida dentro de VAULT_ADDR_RANGE (ej. 0x1000)
        #    Resultado esperado: PermissionError y registro en security_blocks
        ################################################################
        # Construir dirección 0x1000 en R20 (si tu assembler/encode lo requiere)
        LOADI   R20,   0x1000
        # Intento de STORE (debe fallar / ser denegado)
        STORE   R4,    0(R20)     # INTENCIONAL: acceso prohibido a rango de bóveda

        ################################################################
        # 7) Resultados finales: dejar valores en registros para inspección
        #    - R4   : valor leído desde slot 2 (antes de violación)
        #    - R11..R14 : firma (SGEN)
        #    - R15  : flag de verificación (VERIFY)
        #    - R16  : valor final de slot 2 después de KVOP
        #    - Además, consulta las métricas y dump de bóveda en el reporte final del pipeline
        ################################################################

        # Fin del test
