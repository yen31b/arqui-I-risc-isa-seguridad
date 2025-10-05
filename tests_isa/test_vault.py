# test_vault_comprehensive.py

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'isa')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'pipeline')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'vault')))

from vault import KeyVault, VaultAccessError
from keyvault import KeyVault as KeyVaultLegacy
from vault_interface import VaultInterface
from isa_types import UInt64, Vec4x64
from isa_definition import VAULT_SLOTS

class ComprehensiveVaultTest:
    def __init__(self):
        self.tests_passed = 0
        self.tests_failed = 0
        self.detailed_results = []

    def run_test(self, test_func, test_name):
        """Ejecuta un test y registra resultados"""
        print(f"\n{'='*60}")
        print(f"🧪 {test_name}")
        print(f"{'='*60}")
        
        try:
            result = test_func()
            if result:
                self.tests_passed += 1
                self.detailed_results.append(f"✅ {test_name}")
                print(f"✅ {test_name} - PASÓ")
            else:
                self.tests_failed += 1
                self.detailed_results.append(f"❌ {test_name}")
                print(f"❌ {test_name} - FALLÓ")
            return result
        except Exception as e:
            self.tests_failed += 1
            self.detailed_results.append(f"💥 {test_name} - ERROR: {e}")
            print(f"💥 {test_name} - ERROR: {e}")
            import traceback
            traceback.print_exc()
            return False

    def test_keyvault_basic_operations(self):
        """Test de operaciones básicas de KeyVault"""
        
        def test_vault_initialization():
            print("🔍 Testing Inicialización de KeyVault...")
            vault = KeyVault()
            
            # Verificar que todos los slots están inicializados como None
            dump = vault.dump_vault(authorized=True)
            
            print("  Slots iniciales:")
            for slot_name, value in dump.items():
                print(f"    {slot_name}: {value}")
                if value is not None:
                    print(f"    ❌ Slot {slot_name} no está None: {value}")
                    return False
            
            # Verificar contadores iniciales
            counters = vault.get_audit_counters()
            expected_counters = {'reads': 0, 'writes': 0, 'ops': 0}
            if counters != expected_counters:
                print(f"    ❌ Contadores iniciales incorrectos: {counters}")
                return False
            
            print("    ✅ Inicialización correcta")
            return True

        def test_unauthorized_access():
            print("🔍 Testing Acceso No Autorizado...")
            vault = KeyVault()
            
            # Intentar dump sin autorización
            try:
                vault.dump_vault(authorized=False)
                print("    ❌ Debería haber fallado el dump no autorizado")
                return False
            except VaultAccessError:
                print("    ✅ Dump no autorizado bloqueado correctamente")
            
            # Intentar escritura sin autorización
            try:
                vault.write_slot('KEY_0', 0x1234, authorized=False)
                print("    ❌ Debería haber fallado la escritura no autorizada")
                return False
            except VaultAccessError:
                print("    ✅ Escritura no autorizada bloqueada correctamente")
            
            return True

        def test_authorized_operations():
            print("🔍 Testing Operaciones Autorizadas...")
            vault = KeyVault()
            test_value = 0xDEADBEEF12345678
            
            # Escritura autorizada
            vault.write_slot('KEY_0', test_value, authorized=True)
            
            # Verificar escritura
            dump = vault.dump_vault(authorized=True)
            if dump['KEY_0'] != test_value:
                print(f"    ❌ Valor no escrito correctamente: {dump['KEY_0']} != {test_value}")
                return False
            
            # Verificar contadores
            counters = vault.get_audit_counters()
            if counters['writes'] != 1:
                print(f"    ❌ Contador de escrituras incorrecto: {counters['writes']}")
                return False
            
            print(f"    ✅ Escritura autorizada exitosa: KEY_0 = 0x{test_value:x}")
            return True

        def test_slot_validation():
            print("🔍 Testing Validación de Slots...")
            vault = KeyVault()
            
            # Intentar acceder a slot inválido
            try:
                vault.write_slot('SLOT_INVALIDO', 0x1234, authorized=True)
                print("    ❌ Debería haber fallado con slot inválido")
                return False
            except VaultAccessError:
                print("    ✅ Slot inválido detectado correctamente")
            
            # Intentar operación en slot no inicializado
            try:
                vault.access_slot_for_operation('KEY_1', 'KVL')
                print("    ❌ Debería haber fallado con slot no inicializado")
                return False
            except VaultAccessError:
                print("    ✅ Slot no inicializado detectado correctamente")
            
            return True

        # Ejecutar tests básicos
        basic_tests = [
            (test_vault_initialization, "Inicialización de KeyVault"),
            (test_unauthorized_access, "Acceso No Autorizado"),
            (test_authorized_operations, "Operaciones Autorizadas"),
            (test_slot_validation, "Validación de Slots")
        ]
        
        all_passed = True
        for test_func, test_name in basic_tests:
            if not self.run_test(test_func, test_name):
                all_passed = False
        
        return all_passed

    def test_keyvault_advanced_operations(self):
        """Test de operaciones avanzadas de KeyVault"""
        
        def test_operation_access_control():
            print("🔍 Testing Control de Acceso por Operación...")
            vault = KeyVault()
            test_value = 0x1234567890ABCDEF
            
            # Inicializar un slot
            vault.write_slot('KEY_1', test_value, authorized=True)
            
            # Operaciones permitidas
            allowed_operations = ['KVL', 'KVOP', 'SGEN']
            for op in allowed_operations:
                try:
                    result = vault.access_slot_for_operation('KEY_1', op)
                    if int(result) != test_value:
                        print(f"    ❌ Valor incorrecto para operación {op}: {result}")
                        return False
                    print(f"    ✅ Operación {op} permitida correctamente")
                except VaultAccessError as e:
                    print(f"    ❌ Operación {op} debería ser permitida: {e}")
                    return False
            
            # Operación no permitida
            try:
                vault.access_slot_for_operation('KEY_1', 'OPERACION_INVALIDA')
                print("    ❌ Operación inválida debería haber sido bloqueada")
                return False
            except VaultAccessError:
                print("    ✅ Operación inválida bloqueada correctamente")
            
            # Verificar contadores
            counters = vault.get_audit_counters()
            expected_reads = len(allowed_operations)
            if counters['reads'] != expected_reads:
                print(f"    ❌ Contador de lecturas incorrecto: {counters['reads']} != {expected_reads}")
                return False
            
            return True

        def test_signature_generation():
            print("🔍 Testing Generación de Firmas...")
            vault = KeyVault()
            key_value = 0xAABBCCDD11223344
            
            # Configurar llave
            vault.write_slot('KEY_2', key_value, authorized=True)
            
            # Crear estado de hash
            hash_state = Vec4x64(
                0x1111111111111111,
                0x2222222222222222, 
                0x3333333333333333,
                0x4444444444444444
            )
            
            # Generar firma
            signature = vault.generate_signature('KEY_2', hash_state)
            
            # Verificar firma
            expected_values = [
                0x1111111111111111 ^ key_value,
                0x2222222222222222 ^ key_value,
                0x3333333333333333 ^ key_value,
                0x4444444444444444 ^ key_value
            ]
            
            for i, expected in enumerate(expected_values):
                if int(signature[i]) != expected:
                    print(f"    ❌ Firma incorrecta en posición {i}: {signature[i]} != {expected}")
                    return False
            
            print(f"    ✅ Firma generada correctamente: {signature}")
            
            # Verificar contadores
            counters = vault.get_audit_counters()
            if counters['ops'] < 1:  # SGEN cuenta como read + op
                print(f"    ❌ Contador de operaciones incorrecto: {counters['ops']}")
                return False
            
            return True

        def test_multiple_slots_management():
            print("🔍 Testing Gestión de Múltiples Slots...")
            vault = KeyVault()
            
            # Valores de prueba para diferentes slots
            test_data = {
                'KEY_0': 0x1111111111111111,
                'KEY_1': 0x2222222222222222,
                'HASH_A': 0x3333333333333333,
                'HASH_B': 0x4444444444444444
            }
            
            # Escribir en múltiples slots
            for slot_name, value in test_data.items():
                vault.write_slot(slot_name, value, authorized=True)
            
            # Verificar todos los slots
            dump = vault.dump_vault(authorized=True)
            for slot_name, expected_value in test_data.items():
                actual_value = dump.get(slot_name)
                if actual_value != expected_value:
                    print(f"    ❌ Slot {slot_name} incorrecto: {actual_value} != {expected_value}")
                    return False
                print(f"    ✅ Slot {slot_name} = 0x{actual_value:x}")
            
            # Verificar slots no escritos siguen None
            untouched_slots = ['KEY_3', 'HASH_C', 'HASH_D']
            for slot_name in untouched_slots:
                if dump.get(slot_name) is not None:
                    print(f"    ❌ Slot {slot_name} debería ser None: {dump.get(slot_name)}")
                    return False
            
            # Verificar contadores
            counters = vault.get_audit_counters()
            if counters['writes'] != len(test_data):
                print(f"    ❌ Contador de escrituras incorrecto: {counters['writes']} != {len(test_data)}")
                return False
            
            return True

        def test_64bit_mask_operations():
            print("🔍 Testing Operaciones con Máscara 64-bit...")
            vault = KeyVault()
            
            # Test valores que exceden 64 bits
            large_values = [
                0xFFFFFFFFFFFFFFFF,  # máximo 64 bits
                0x1FFFFFFFFFFFFFFFF, # 65 bits - debería ser truncado
                0x1234567890ABCDEF1234567890ABCDEF  # 128 bits - debería ser truncado
            ]
            
            for i, large_value in enumerate(large_values):
                vault.write_slot(f'KEY_{i}', large_value, authorized=True)
                stored_value = vault.access_slot_for_operation(f'KEY_{i}', 'KVL')
                
                # Verificar que está truncado a 64 bits
                expected = large_value & 0xFFFFFFFFFFFFFFFF
                if int(stored_value) != expected:
                    print(f"    ❌ Truncado incorrecto: {stored_value} != {expected}")
                    return False
                print(f"    ✅ Valor 0x{large_value:x} truncado correctamente a 0x{stored_value:x}")
            
            return True

        # Ejecutar tests avanzados
        advanced_tests = [
            (test_operation_access_control, "Control de Acceso por Operación"),
            (test_signature_generation, "Generación de Firmas"),
            (test_multiple_slots_management, "Gestión de Múltiples Slots"),
            (test_64bit_mask_operations, "Operaciones con Máscara 64-bit")
        ]
        
        all_passed = True
        for test_func, test_name in advanced_tests:
            if not self.run_test(test_func, test_name):
                all_passed = False
        
        return all_passed

    def test_vault_interface_integration(self):
        """Test de VaultInterface e integración con KeyVault"""
        
        def test_interface_initialization():
            print("🔍 Testing Inicialización de VaultInterface...")
            interface = VaultInterface()
            
            # Verificar métricas iniciales
            report = interface.get_security_report()
            expected_initial = {
                'vault_ops': 0,
                'security_violations': 0,
                'atomic_operations': 0,
                'vault_reads': 0,
                'vault_writes': 0,
                'vault_operations': 0
            }
            
            if report != expected_initial:
                print(f"    ❌ Reporte inicial incorrecto: {report}")
                return False
            
            print("    ✅ VaultInterface inicializado correctamente")
            return True

        def test_control_signals_generation():
            print("🔍 Testing Generación de Señales de Control...")
            interface = VaultInterface()
            
            test_cases = [
                {
                    'opcode': 'VSTORE',
                    'operands': {'vault_idx': 2},
                    'expected': {
                        'vault_op': True,
                        'needs_authorization': True,
                        'atomic_operation': False,
                        'slot_index': 2
                    }
                },
                {
                    'opcode': 'SIGN', 
                    'operands': {'vault_idx': 1},
                    'expected': {
                        'vault_op': True,
                        'needs_authorization': True,
                        'atomic_operation': True,
                        'slot_index': 1
                    }
                },
                {
                    'opcode': 'ADD',  # No es operación de bóveda
                    'operands': {},
                    'expected': {
                        'vault_op': False,
                        'needs_authorization': False,
                        'atomic_operation': False,
                        'slot_index': None
                    }
                }
            ]
            
            for i, test_case in enumerate(test_cases):
                signals = interface.generate_control_signals(
                    test_case['opcode'], 
                    test_case['operands']
                )
                
                if signals != test_case['expected']:
                    print(f"    ❌ Señales incorrectas para {test_case['opcode']}: {signals}")
                    return False
                print(f"    ✅ Señales correctas para {test_case['opcode']}")
            
            return True

        def test_vault_operations_execution():
            print("🔍 Testing Ejecución de Operaciones de Bóveda...")
            interface = VaultInterface()
            
            # Test KVW (Key Vault Write)
            interface.execute_vault_operation('KVW', 0, value=0x1234567890ABCDEF)
            
            # Test KVL (Key Vault Load)
            result = interface.execute_vault_operation('KVL', 0)
            if int(result) != 0x1234567890ABCDEF:
                print(f"    ❌ KVL retornó valor incorrecto: {result}")
                return False
            print(f"    ✅ KVL operación exitosa: 0x{result:x}")
            
            # Test KVOP (Key Vault Operation)
            result = interface.execute_vault_operation('KVOP', 0)
            if int(result) != 0x1234567890ABCDEF:
                print(f"    ❌ KVOP retornó valor incorrecto: {result}")
                return False
            print(f"    ✅ KVOP operación exitosa: 0x{result:x}")
            
            # Verificar métricas
            report = interface.get_security_report()
            if report['vault_ops'] != 3:
                print(f"    ❌ Contador de operaciones incorrecto: {report['vault_ops']}")
                return False
            if report['atomic_operations'] != 1:  # Solo KVOP es atómico
                print(f"    ❌ Contador de operaciones atómicas incorrecto: {report['atomic_operations']}")
                return False
            
            return True

        def test_signature_operation():
            print("🔍 Testing Operación de Firma...")
            interface = VaultInterface()
            
            # Configurar llave
            interface.execute_vault_operation('KVW', 1, value=0xAAAAAAAAAAAAAAAA)
            
            # Crear estado de hash
            hash_state = Vec4x64(
                0x1111111111111111,
                0x2222222222222222,
                0x3333333333333333, 
                0x4444444444444444
            )
            
            # Generar firma
            signature = interface.execute_vault_operation('SGEN', 1, state=hash_state)
            
            # Verificar firma
            expected_signature = hash_state.xor_with_key(0xAAAAAAAAAAAAAAAA)
            for i in range(4):
                if int(signature[i]) != int(expected_signature[i]):
                    print(f"    ❌ Firma incorrecta en posición {i}")
                    return False
            
            print(f"    ✅ Firma generada correctamente: {signature}")
            
            # Verificar métricas
            report = interface.get_security_report()
            if report['atomic_operations'] < 1:
                print(f"    ❌ Operación de firma no contada como atómica")
                return False
            
            return True

# En test_vault.py 
        def test_error_handling():
            print("🔍 Testing Manejo de Errores...")
            interface = VaultInterface()
            
            initial_violations = interface.get_security_report()['security_violations']
            violations_count = 0
            
            # Test índice inválido
            try:
                interface.execute_vault_operation('KVL', 15)  # Índice fuera de rango
                print("    ❌ Debería haber fallado con índice inválido")
                return False
            except (ValueError, VaultAccessError) as e:
                print(f"    ✅ Índice inválido detectado: {e}")
                violations_count += 1
            
            # Test operación no soportada
            try:
                interface.execute_vault_operation('OPERACION_INVALIDA', 0)
                print("    ❌ Debería haber fallado con operación no soportada")
                return False
            except ValueError as e:
                print(f"    ✅ Operación no soportada detectada: {e}")
                violations_count += 1
            
            # Test estado inválido para firma
            try:
                interface.execute_vault_operation('SGEN', 0, state="invalid_state")
                print("    ❌ Debería haber fallado con estado inválido")
                return False
            except (ValueError, TypeError, VaultAccessError) as e:
                print(f"    ✅ Estado inválido detectado: {e}")
                violations_count += 1
            
            # Verificar que se incrementaron las violaciones de seguridad
            final_report = interface.get_security_report()
            expected_violations = initial_violations + violations_count
            
            print(f"  Violaciones esperadas: {expected_violations}, actuales: {final_report['security_violations']}")
            
            if final_report['security_violations'] != expected_violations:
                print(f"    ❌ Violaciones de seguridad no contadas correctamente: {final_report['security_violations']} != {expected_violations}")
                return False
            
            print(f"    ✅ Todas las violaciones contadas correctamente")
            return True

        # Ejecutar tests de interfaz
        interface_tests = [
            (test_interface_initialization, "Inicialización de VaultInterface"),
            (test_control_signals_generation, "Generación de Señales de Control"),
            (test_vault_operations_execution, "Ejecución de Operaciones de Bóveda"),
            (test_signature_operation, "Operación de Firma"),
            (test_error_handling, "Manejo de Errores")
        ]
        
        all_passed = True
        for test_func, test_name in interface_tests:
            if not self.run_test(test_func, test_name):
                all_passed = False
        
        return all_passed

    def test_backward_compatibility(self):
        """Test de compatibilidad con KeyVault legacy"""
        
        def test_legacy_keyvault_compatibility():
            print("🔍 Testing Compatibilidad con KeyVault Legacy...")
            
            # Test que keyvault.py puede importarse y usarse
            try:
                legacy_vault = KeyVaultLegacy()
                print("    ✅ KeyVault legacy importado correctamente")
            except Exception as e:
                print(f"    ❌ Error importando KeyVault legacy: {e}")
                return False
            
            # Test operaciones básicas en legacy
            legacy_vault.write_slot('KEY_0', 0x1234, authorized=True)
            value = legacy_vault.access_slot_for_operation('KEY_0', 'KVL')
            
            if int(value) != 0x1234:
                print(f"    ❌ KeyVault legacy operación incorrecta: {value}")
                return False
            
            print("    ✅ KeyVault legacy funciona correctamente")
            return True

        def test_cross_compatibility():
            print("🔍 Testing Compatibilidad Cruzada...")
            
            # Crear instancias de ambas implementaciones
            modern_vault = KeyVault()
            legacy_vault = KeyVaultLegacy()
            
            # Escribir mismo valor en ambos
            test_value = 0x5555555555555555
            modern_vault.write_slot('KEY_0', test_value, authorized=True)
            legacy_vault.write_slot('KEY_0', test_value, authorized=True)
            
            # Leer de ambos y comparar
            modern_val = modern_vault.access_slot_for_operation('KEY_0', 'KVL')
            legacy_val = legacy_vault.access_slot_for_operation('KEY_0', 'KVL')
            
            if int(modern_val) != int(legacy_val):
                print(f"    ❌ Valores diferentes entre implementaciones: {modern_val} != {legacy_val}")
                return False
            
            print("    ✅ Compatibilidad cruzada verificada")
            return True

        return self.run_test(test_legacy_keyvault_compatibility, "Compatibilidad con KeyVault Legacy") and \
               self.run_test(test_cross_compatibility, "Compatibilidad Cruzada")

    def test_security_audit_trail(self):
        """Test de auditoría de seguridad y trazabilidad"""
        
        def test_comprehensive_audit_trail():
            print("🔍 Testing Auditoría Integral...")
            interface = VaultInterface()
            
            # Realizar múltiples operaciones
            operations = [
                ('KVW', 0, {'value': 0x1111}),
                ('KVW', 1, {'value': 0x2222}),
                ('KVL', 0, {}),
                ('KVOP', 1, {}),
                ('KVW', 2, {'value': 0x3333}),
                ('KVL', 2, {})
            ]
            
            for op, idx, kwargs in operations:
                interface.execute_vault_operation(op, idx, **kwargs)
            
            # Verificar reporte final
            report = interface.get_security_report()
            
            print("  📊 Reporte de auditoría:")
            for key, value in report.items():
                print(f"    {key}: {value}")
            
            # Verificaciones específicas
            if report['vault_ops'] != len(operations):
                print(f"    ❌ Total de operaciones incorrecto: {report['vault_ops']}")
                return False
            
            if report['vault_writes'] != 3:  # 3 KVW
                print(f"    ❌ Escrituras incorrectas: {report['vault_writes']}")
                return False
            
            if report['vault_reads'] != 3:  # 2 KVL + 1 KVOP
                print(f"    ❌ Lecturas incorrectas: {report['vault_reads']}")
                return False
            
            if report['atomic_operations'] != 1:  # 1 KVOP
                print(f"    ❌ Operaciones atómicas incorrectas: {report['atomic_operations']}")
                return False
            
            print("    ✅ Auditoría integral correcta")
            return True

        def test_security_violation_tracking():
            print("🔍 Testing Seguimiento de Violaciones de Seguridad...")
            interface = VaultInterface()
            
            initial_report = interface.get_security_report()
            initial_violations = initial_report['security_violations']
            
            print(f"  Violaciones iniciales: {initial_violations}")
            
            # Provocar una violación de seguridad con índice REALMENTE inválido
            try:
                # Usar índice fuera del rango de slots (8 slots = índices 0-7)
                interface.execute_vault_operation('KVL', 15)  # Índice 15 no existe
                print("    ❌ Debería haber lanzado excepción")
                return False
            except (ValueError, VaultAccessError) as e:
                print(f"    ✅ Excepción capturada correctamente: {e}")
            
            # Verificar que se incrementó el contador
            final_report = interface.get_security_report()
            print(f"  Violaciones finales: {final_report['security_violations']}")
            
            if final_report['security_violations'] <= initial_violations:
                print(f"    ❌ Violación de seguridad no registrada: {final_report['security_violations']} (inicial: {initial_violations})")
                return False
            
            print(f"    ✅ Violación de seguridad registrada: {final_report['security_violations']}")
            return True

        return self.run_test(test_comprehensive_audit_trail, "Auditoría Integral") and \
               self.run_test(test_security_violation_tracking, "Seguimiento de Violaciones de Seguridad")

    def run_comprehensive_vault_test(self):
        """Ejecuta todos los tests comprehensivos del sistema de bóveda"""
        print("🚀 INICIANDO TEST SUITE COMPLETO DEL SISTEMA DE BÓVEDA")
        print("=" * 70)
        
        test_suites = [
            (self.test_keyvault_basic_operations, "Operaciones Básicas de KeyVault"),
            (self.test_keyvault_advanced_operations, "Operaciones Avanzadas de KeyVault"),
            (self.test_vault_interface_integration, "Integración con VaultInterface"),
            (self.test_backward_compatibility, "Compatibilidad con Versiones Anteriores"),
            (self.test_security_audit_trail, "Auditoría de Seguridad")
        ]
        
        for test_suite, suite_name in test_suites:
            print(f"\n{'#'*70}")
            print(f"📋 SUITE: {suite_name}")
            print(f"{'#'*70}")
            test_suite()
        
        # Reporte final
        print(f"\n{'='*70}")
        print("📊 REPORTE FINAL COMPLETO - SISTEMA DE BÓVEDA")
        print(f"{'='*70}")
        print(f"✅ Tests pasados: {self.tests_passed}")
        print(f"❌ Tests fallados: {self.tests_failed}")
        print(f"📈 Total de tests: {self.tests_passed + self.tests_failed}")
        
        print(f"\n📋 Resultados detallados:")
        for result in self.detailed_results:
            print(f"  {result}")
        
        success_rate = (self.tests_passed / (self.tests_passed + self.tests_failed)) * 100 if (self.tests_passed + self.tests_failed) > 0 else 0
        print(f"\n🎯 Tasa de éxito: {success_rate:.1f}%")
        
        if self.tests_failed == 0:
            print("\n🎉 ¡TODOS LOS TESTS DEL SISTEMA DE BÓVEDA PASARON EXITOSAMENTE!")
            return True
        else:
            print(f"\n💥 {self.tests_failed} test(s) fallaron - Revisar implementación")
            return False

# Ejecutar el test suite completo
if __name__ == "__main__":
    vault_test_suite = ComprehensiveVaultTest()
    success = vault_test_suite.run_comprehensive_vault_test()
    
    sys.exit(0 if success else 1)