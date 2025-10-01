# test_decode_debug.py

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'isa')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'pipeline')))

from isa_definition import encode_instruction, OPCODES, get_field_value, INST_FORMATS
from decode_stage import DecodeStage
from register_file import register_file

def test_decode_instruction():
    """Test específico del decode stage"""
    print("🔍 TEST ESPECÍFICO DEL DECODE STAGE")
    print("=" * 50)
    
    # Probar ADDI R1, R0, 10
    instruction = encode_instruction('I_TYPE', opcode=OPCODES['ADDI'], rd=1, rs1=0, imm=10)
    
    print(f"Instrucción codificada: 0x{instruction:08x}")
    print(f"Binario: {instruction:032b}")
    
    # Verificar campos manualmente
    print("\n📊 Análisis manual de campos:")
    opcode_manual = (instruction >> 26) & 0x3F  # bits 31-26
    rd_manual = (instruction >> 21) & 0x1F      # bits 25-21  
    rs1_manual = (instruction >> 16) & 0x1F     # bits 20-16
    imm_manual = instruction & 0xFFFF           # bits 15-0
    
    print(f"Opcode (bits 31-26): {opcode_manual} (0x{opcode_manual:x})")
    print(f"RD (bits 25-21): {rd_manual} (0x{rd_manual:x})")
    print(f"RS1 (bits 20-16): {rs1_manual} (0x{rs1_manual:x})")
    print(f"IMM (bits 15-0): {imm_manual} (0x{imm_manual:x})")
    
    # Probar decode stage
    print("\n🔧 Probando DecodeStage:")
    rf = register_file()
    decode = DecodeStage(rf)
    
    decoded = decode.decode(instruction)
    
    print(f"Opcode name: {decoded['opcode_name']}")
    print(f"Format type: {decoded['format_type']}")
    print(f"Operandos: {decoded['operandos']}")
    
    # Verificar que el inmediato sea correcto
    imm_decoded = decoded['operandos'].get('imm', 'NO ENCONTRADO')
    print(f"Immediato decodificado: {imm_decoded}")
    
    if imm_decoded == 10:
        print("✅ ¡DECODE FUNCIONA CORRECTAMENTE!")
    else:
        print(f"❌ PROBLEMA: imm = {imm_decoded}, esperado 10")

def test_different_instructions():
    """Test con diferentes instrucciones"""
    print("\n🧪 TEST CON DIFERENTES INSTRUCCIONES")
    print("=" * 45)
    
    instructions = [
        ("ADDI R1, R0, 10", encode_instruction('I_TYPE', opcode=OPCODES['ADDI'], rd=1, rs1=0, imm=10)),
        ("ADDI R2, R0, 255", encode_instruction('I_TYPE', opcode=OPCODES['ADDI'], rd=2, rs1=0, imm=255)),
        ("ADDI R3, R0, 0x123", encode_instruction('I_TYPE', opcode=OPCODES['ADDI'], rd=3, rs1=0, imm=0x123)),
        ("ADD R4, R1, R2", encode_instruction('R_TYPE', opcode=OPCODES['ADD'], rd=4, rs1=1, rs2=2, funct=0)),
    ]
    
    rf = register_file()
    decode = DecodeStage(rf)
    
    for desc, instr in instructions:
        print(f"\n🔹 {desc}: 0x{instr:08x}")
        decoded = decode.decode(instr)
        print(f"  Formato: {decoded['format_type']}")
        print(f"  Operandos: {decoded['operandos']}")

if __name__ == "__main__":
    test_decode_instruction()
    test_different_instructions()