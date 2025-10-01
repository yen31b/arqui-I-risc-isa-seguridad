# test_pipeline_comprehensive.py

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'isa')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'pipeline')))

from isa_definition import encode_instruction, OPCODES, INST_FORMATS
from pipeline import Pipeline
from register_file import register_file
from fetch_stage import FetchStage, InstructionMemory
from decode_stage import DecodeStage
from execute_stage import ExecuteStage
from memory_stage import MemoryStage, DataMemory
from writeback_stage import WriteBackStage

class ComprehensivePipelineTest:
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

    def test_individual_stages(self):
        """Test de cada etapa del pipeline individualmente"""
        
        def test_fetch_stage():
            print("🔍 Testing Fetch Stage...")
            rf = register_file()
            rf.write('PC', 0)
            instructions = [0x12345678, 0xABCDEF01, 0xDEADBEEF]
            instr_mem = InstructionMemory(instructions)
            fetch = FetchStage(rf, instr_mem)
            
            # Test múltiples fetches
            for i, expected_instr in enumerate(instructions):
                instr = fetch.step()
                pc_expected = (i + 1) * 4
                pc_actual = rf.read('PC')
                
                print(f"  Fetch {i}: instrucción=0x{instr:08x}, PC={pc_actual}")
                
                if instr != expected_instr:
                    print(f"    ❌ Instrucción incorrecta: 0x{instr:08x} != 0x{expected_instr:08x}")
                    return False
                if pc_actual != pc_expected:
                    print(f"    ❌ PC incorrecto: {pc_actual} != {pc_expected}")
                    return False
            
            metrics = fetch.get_metrics()
            if metrics['fetch_count'] != len(instructions):
                print(f"    ❌ Métricas incorrectas: {metrics}")
                return False
            
            print("    ✅ Fetch Stage - OK")
            return True

        def test_decode_stage():
            print("🔍 Testing Decode Stage...")
            rf = register_file()
            decode = DecodeStage(rf)
            
            # Test diferentes formatos de instrucción
            test_instructions = [
                # (instrucción, formato_esperado, opcode_esperado)
                (encode_instruction('I_TYPE', opcode=OPCODES['ADDI'], rd=1, rs1=0, imm=10), 'I_TYPE', 'ADDI'),
                (encode_instruction('R_TYPE', opcode=OPCODES['ADD'], rd=3, rs1=1, rs2=2, funct=0), 'R_TYPE', 'ADD'),
                (encode_instruction('I_TYPE', opcode=OPCODES['ANDI'], rd=5, rs1=4, imm=0xFF), 'I_TYPE', 'ANDI'),
            ]
            
            for instr, expected_format, expected_opcode in test_instructions:
                decoded = decode.decode(instr)
                
                print(f"  Instrucción 0x{instr:08x}:")
                print(f"    Formato: {decoded['format_type']} (esperado: {expected_format})")
                print(f"    Opcode: {decoded['opcode_name']} (esperado: {expected_opcode})")
                
                if decoded['format_type'] != expected_format:
                    print(f"    ❌ Formato incorrecto")
                    return False
                if decoded['opcode_name'] != expected_opcode:
                    print(f"    ❌ Opcode incorrecto")
                    return False
                
                # Verificar operandos según formato
                if expected_format == 'I_TYPE':
                    if 'imm' not in decoded['operandos']:
                        print(f"    ❌ Falta campo 'imm' en I_TYPE")
                        return False
                elif expected_format == 'R_TYPE':
                    if 'rs1' not in decoded['operandos'] or 'rs2' not in decoded['operandos']:
                        print(f"    ❌ Faltan campos en R_TYPE")
                        return False
            
            print("    ✅ Decode Stage - OK")
            return True

        def test_execute_stage():
            print("🔍 Testing Execute Stage...")
            execute = ExecuteStage()
            
            test_cases = [
                {
                    'name': 'ADDI R1, R0, 10',
                    'decoded': {
                        'opcode_name': 'ADDI',
                        'format_type': 'I_TYPE',
                        'operandos': {'rs1_val': 0, 'imm': 10},
                        'control_signals': {'is_arithmetic': True}
                    },
                    'expected_result': 10
                },
                {
                    'name': 'ADD R3, R1, R2',
                    'decoded': {
                        'opcode_name': 'ADD',
                        'format_type': 'R_TYPE', 
                        'operandos': {'rs1_val': 15, 'rs2_val': 25},
                        'control_signals': {'is_arithmetic': True}
                    },
                    'expected_result': 40
                },
                {
                    'name': 'AND R4, R1, R2',
                    'decoded': {
                        'opcode_name': 'AND',
                        'format_type': 'R_TYPE',
                        'operandos': {'rs1_val': 0xFF, 'rs2_val': 0xF0},
                        'control_signals': {'is_arithmetic': True}
                    },
                    'expected_result': 0xF0
                },
            ]
            
            for test_case in test_cases:
                result = execute.execute(test_case['decoded'])
                result_value = int(result['result']) if hasattr(result['result'], 'value') else int(result['result'])
                
                print(f"  {test_case['name']}:")
                print(f"    Resultado: {result_value} (esperado: {test_case['expected_result']})")
                
                if result_value != test_case['expected_result']:
                    print(f"    ❌ Resultado incorrecto")
                    return False
            
            print("    ✅ Execute Stage - OK")
            return True

        def test_memory_stage():
            print("🔍 Testing Memory Stage...")
            data_mem = DataMemory()
            memory = MemoryStage(data_mem)
            
            # Test operaciones de memoria - CORREGIDO
            test_cases = [
                {
                    'name': 'STORE value',
                    'ex_result': {'result': 0x100, 'latency': 1},  # dirección
                    'decoded': {
                        'opcode_name': 'STORE',
                        'operandos': {'rs2_val': 0x123},  # ✅ CORRECCIÓN: rs2_val contiene el valor
                        'control_signals': {'use_boveda': False}
                    }
                },
                {
                    'name': 'LOAD value', 
                    'ex_result': {'result': 0x100, 'latency': 1},  # dirección
                    'decoded': {
                        'opcode_name': 'LOAD',
                        'operandos': {},  # ✅ Sin operandos específicos para LOAD
                        'control_signals': {'use_boveda': False}
                    }
                }
            ]
            
            # Primero escribir un valor
            memory.execute(test_cases[0]['ex_result'], test_cases[0]['decoded'])
            
            # Luego leerlo
            result = memory.execute(test_cases[1]['ex_result'], test_cases[1]['decoded'])
            loaded_value = int(result['result']) if result['result'] else 0
            
            print(f"  Valor almacenado: 0x123")
            print(f"  Valor leído: 0x{loaded_value:x}")
            
            if loaded_value != 0x123:
                print(f"    ❌ Error en operaciones de memoria")
                return False
            
            print("    ✅ Memory Stage - OK")
            return True

        def test_writeback_stage():
            print("🔍 Testing Writeback Stage...")
            rf = register_file()
            wb = WriteBackStage(rf)
            
            test_cases = [
                {
                    'name': 'Write to R5',
                    'mem_result': {'result': 0xDEADBEEF},
                    'decoded': {
                        'opcode_name': 'ADDI', 
                        'operandos': {'rd': 5}
                    },
                    'expected_reg': 'R5',
                    'expected_value': 0xDEADBEEF
                }
            ]
            
            for test_case in test_cases:
                wb.execute(test_case['mem_result'], test_case['decoded'])
                
                reg_value = rf.read(test_case['expected_reg'])
                reg_value_int = int(reg_value) if hasattr(reg_value, 'value') else int(reg_value)
                
                print(f"  {test_case['name']}:")
                print(f"    Valor en {test_case['expected_reg']}: 0x{reg_value_int:x} (esperado: 0x{test_case['expected_value']:x})")
                
                if reg_value_int != test_case['expected_value']:
                    print(f"    ❌ Escritura incorrecta")
                    return False
            
            print("    ✅ Writeback Stage - OK")
            return True

        # Ejecutar todos los tests de etapas individuales
        stage_tests = [
            (test_fetch_stage, "Fetch Stage"),
            (test_decode_stage, "Decode Stage"), 
            (test_execute_stage, "Execute Stage"),
            (test_memory_stage, "Memory Stage"),
            (test_writeback_stage, "Writeback Stage")
        ]
        
        all_passed = True
        for test_func, test_name in stage_tests:
            if not self.run_test(test_func, test_name):
                all_passed = False
        
        return all_passed

    def test_instruction_types(self):
        """Test de diferentes tipos de instrucciones"""
        
        def test_arithmetic_instructions():
            print("🔍 Testing Instrucciones Aritméticas...")
            
            instructions = [
            encode_instruction('I_TYPE', opcode=OPCODES['ADDI'], rd=1, rs1=0, imm=5),
            encode_instruction('I_TYPE', opcode=OPCODES['ADDI'], rd=2, rs1=0, imm=3),
            encode_instruction('R_TYPE', opcode=OPCODES['ADD'], rd=3, rs1=1, rs2=2, funct=0),
            encode_instruction('R_TYPE', opcode=OPCODES['SUB'], rd=4, rs1=3, rs2=1, funct=0),  # R4 = R3 - R1 = 8 - 5 = 3
            encode_instruction('R_TYPE', opcode=OPCODES['AND'], rd=5, rs1=1, rs2=2, funct=0),  # R5 = 5 & 3 = 1
            encode_instruction('R_TYPE', opcode=OPCODES['OR'], rd=6, rs1=1, rs2=2, funct=0),   # R6 = 5 | 3 = 7
        ]
            
            pipe = Pipeline(instructions)
            pipe.run()
            
            results = {
                'R1': int(pipe.rf.read('R1')),
                'R2': int(pipe.rf.read('R2')),
                'R3': int(pipe.rf.read('R3')),
                'R4': int(pipe.rf.read('R4')),
                'R5': int(pipe.rf.read('R5')),
                'R6': int(pipe.rf.read('R6')),
            }
            
            expected = {
                'R1': 5,    # ADDI R1, R0, 5
                'R2': 3,    # ADDI R2, R0, 3  
                'R3': 8,    # ADD R3, R1, R2 (5+3=8)
                'R4': 3,    # SUB R4, R3, R1 (8-5=3) - CORREGIDO: debería ser 5? Revisar
                'R5': 1,    # AND R5, R1, R2 (5 & 3 = 1)
                'R6': 7,    # OR R6, R1, R2 (5 | 3 = 7)
            }
            
            all_correct = True
            for reg, value in results.items():
                expected_val = expected[reg]
                print(f"  {reg}: {value} (esperado: {expected_val})")
                if value != expected_val:
                    print(f"    ❌ Valor incorrecto en {reg}")
                    all_correct = False
            
            return all_correct

        def test_memory_instructions():
            print("🔍 Testing Instrucciones de Memoria...")
            
            instructions = [
                encode_instruction('I_TYPE', opcode=OPCODES['ADDI'], rd=1, rs1=0, imm=0x100),  # R1 = dirección
                encode_instruction('I_TYPE', opcode=OPCODES['ADDI'], rd=2, rs1=0, imm=0xABC),  # R2 = valor a almacenar
                encode_instruction('S_TYPE', opcode=OPCODES['STORE'], rs1=1, rs2=2, imm=0),    # STORE [R1], R2
                encode_instruction('I_TYPE', opcode=OPCODES['LOAD'], rd=3, rs1=1, imm=0),      # LOAD R3, [R1]
            ]
            
            pipe = Pipeline(instructions)
            pipe.run()
            
            loaded_value = int(pipe.rf.read('R3'))
            expected_value = 0xABC
            
            print(f"  Valor almacenado: 0x{expected_value:x}")
            print(f"  Valor leído: 0x{loaded_value:x}")
            
            if loaded_value != expected_value:
                print(f"    ❌ Error en operaciones de memoria")
                return False
            
            return True

        def test_immediate_instructions():
            print("🔍 Testing Instrucciones con Inmediatos...")
            
            test_values = [10, 255, 0x123, 0x7FFF, 0xFFFF]
            all_passed = True
            
            for i, imm_val in enumerate(test_values):
                instructions = [
                    encode_instruction('I_TYPE', opcode=OPCODES['ADDI'], rd=10+i, rs1=0, imm=imm_val)
                ]
                
                pipe = Pipeline(instructions)
                pipe.run()
                
                result = int(pipe.rf.read(f'R{10+i}'))
                print(f"  ADDI R{10+i}, R0, {imm_val} (0x{imm_val:x}) → R{10+i} = {result} (0x{result:x})")
                
                if result != imm_val:
                    print(f"    ❌ Error con inmediato 0x{imm_val:x}")
                    all_passed = False
            
            return all_passed

        # Ejecutar tests de tipos de instrucciones
        instruction_tests = [
            (test_arithmetic_instructions, "Instrucciones Aritméticas"),
            (test_memory_instructions, "Instrucciones de Memoria"),
            (test_immediate_instructions, "Instrucciones con Inmediatos")
        ]
        
        all_passed = True
        for test_func, test_name in instruction_tests:
            if not self.run_test(test_func, test_name):
                all_passed = False
        
        return all_passed

    def test_pipeline_metrics(self):
        """Test de métricas y rendimiento del pipeline"""
        
        def test_metrics_collection():
            print("🔍 Testing Recolección de Métricas...")
            
            instructions = [
                encode_instruction('I_TYPE', opcode=OPCODES['ADDI'], rd=1, rs1=0, imm=10),
                encode_instruction('I_TYPE', opcode=OPCODES['ADDI'], rd=2, rs1=0, imm=20),
                encode_instruction('R_TYPE', opcode=OPCODES['ADD'], rd=3, rs1=1, rs2=2, funct=0),
                encode_instruction('I_TYPE', opcode=OPCODES['LOAD'], rd=4, rs1=1, imm=0),
            ]
            
            pipe = Pipeline(instructions)
            pipe.run()
            
            metrics = pipe.get_metrics()
            
            print("📊 Métricas del Pipeline:")
            print(f"  Ciclos totales: {metrics['total_cycles']}")
            print(f"  Instrucciones completadas: {metrics['instructions_completed']}")
            print(f"  Fetch count: {metrics['fetch']['fetch_count']}")
            print(f"  Decode count: {metrics['decode']['decode_count']}")
            print(f"  Execute count: {metrics['execute']['exec_count']}")
            print(f"  Writebacks: {metrics['writeback']['writebacks']}")
            
            # Verificar métricas básicas
            if metrics['instructions_completed'] != len(instructions):
                print(f"    ❌ Instrucciones completadas incorrectas")
                return False
            
            if metrics['fetch']['fetch_count'] != len(instructions):
                print(f"    ❌ Fetch count incorrecto")
                return False
            
            return True

        def test_performance_analysis():
            print("🔍 Testing Análisis de Rendimiento...")
            
            # Programa con diferentes latencias
            instructions = [
                encode_instruction('I_TYPE', opcode=OPCODES['ADDI'], rd=1, rs1=0, imm=1),    # latencia 1
                encode_instruction('R_TYPE', opcode=OPCODES['MULMOD'], rd=2, rs1=1, rs2=1, funct=0),  # latencia 3
                encode_instruction('I_TYPE', opcode=OPCODES['ADDI'], rd=3, rs1=0, imm=100),  # latencia 1
            ]
            
            pipe = Pipeline(instructions)
            pipe.run()
            
            metrics = pipe.get_metrics()
            exec_metrics = metrics['execute']
            
            print("📈 Análisis de Rendimiento:")
            print(f"  Ciclos ejecución: {exec_metrics['cycles']}")
            print(f"  Operaciones ejecutadas: {exec_metrics['exec_count']}")
            print(f"  Latencias: {exec_metrics['op_latency']}")
            
            # Verificar que se registraron las latencias
            if 'MULMOD' not in exec_metrics['op_latency']:
                print(f"    ❌ No se registró latencia de MULMOD")
                return False
            
            if exec_metrics['op_latency']['MULMOD'] != 3:
                print(f"    ❌ Latencia de MULMOD incorrecta")
                return False
            
            return True

        return self.run_test(test_metrics_collection, "Recolección de Métricas") and \
               self.run_test(test_performance_analysis, "Análisis de Rendimiento")

    def test_edge_cases(self):
        """Test de casos límite y errores"""
        
        def test_unknown_instruction():
            print("🔍 Testing Instrucción Desconocida...")
            
            instructions = [0xFFFFFFFF]  # Instrucción inválida
            
            pipe = Pipeline(instructions)
            pipe.run()  # No debería crashear
            
            # Verificar que se completó sin errores fatales
            metrics = pipe.get_metrics()
            if metrics['instructions_completed'] > 0:
                print("    ✅ Manejo de instrucción desconocida - OK")
                return True
            else:
                print("    ❌ No se procesó instrucción desconocida")
                return False

        def test_empty_program():
            print("🔍 Testing Programa Vacío...")
            
            instructions = []
            
            pipe = Pipeline(instructions)
            pipe.run()
            
            metrics = pipe.get_metrics()
            if metrics['instructions_completed'] == 0:
                print("    ✅ Programa vacío manejado correctamente")
                return True
            else:
                print("    ❌ Programa vacío no manejado correctamente")
                return False

        def test_register_initialization():
            print("🔍 Testing Inicialización de Registros...")
            
            rf = register_file()
            
            # Verificar que R0 es cero
            r0_val = rf.read('R0')
            if int(r0_val) != 0:
                print(f"    ❌ R0 no es cero: {r0_val}")
                return False
            
            # Verificar que PC inicia en 0
            pc_val = rf.read('PC')
            if int(pc_val) != 0:
                print(f"    ❌ PC no inicia en 0: {pc_val}")
                return False
            
            print("    ✅ Inicialización de registros - OK")
            return True

        edge_tests = [
            (test_unknown_instruction, "Instrucción Desconocida"),
            (test_empty_program, "Programa Vacío"),
            (test_register_initialization, "Inicialización de Registros")
        ]
        
        all_passed = True
        for test_func, test_name in edge_tests:
            if not self.run_test(test_func, test_name):
                all_passed = False
        
        return all_passed

    def run_comprehensive_test(self):
        """Ejecuta todos los tests comprehensivos"""
        print("🚀 INICIANDO TEST SUITE COMPLETO DEL PIPELINE")
        print("=" * 70)
        
        test_suites = [
            (self.test_individual_stages, "Etapas Individuales del Pipeline"),
            (self.test_instruction_types, "Tipos de Instrucciones"),
            (self.test_pipeline_metrics, "Métricas y Rendimiento"),
            (self.test_edge_cases, "Casos Límite y Errores")
        ]
        
        for test_suite, suite_name in test_suites:
            print(f"\n{'#'*70}")
            print(f"📋 SUITE: {suite_name}")
            print(f"{'#'*70}")
            test_suite()
        
        # Reporte final
        print(f"\n{'='*70}")
        print("📊 REPORTE FINAL COMPLETO")
        print(f"{'='*70}")
        print(f"✅ Tests pasados: {self.tests_passed}")
        print(f"❌ Tests fallados: {self.tests_failed}")
        print(f"📈 Total de tests: {self.tests_passed + self.tests_failed}")
        
        print(f"\n📋 Resultados detallados:")
        for result in self.detailed_results:
            print(f"  {result}")
        
        success_rate = (self.tests_passed / (self.tests_passed + self.tests_failed)) * 100
        print(f"\n🎯 Tasa de éxito: {success_rate:.1f}%")
        
        if self.tests_failed == 0:
            print("\n🎉 ¡TODOS LOS TESTS PASARON EXITOSAMENTE!")
            return True
        else:
            print(f"\n💥 {self.tests_failed} test(s) fallaron - Revisar implementación")
            return False

# Ejecutar el test suite completo
if __name__ == "__main__":
    test_suite = ComprehensivePipelineTest()
    success = test_suite.run_comprehensive_test()
    
    sys.exit(0 if success else 1)