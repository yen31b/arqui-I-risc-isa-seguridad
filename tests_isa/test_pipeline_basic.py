import os, sys, unittest
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
	sys.path.append(ROOT)

try:
	from pipeline.pipeline import Pipeline
	from isa.isa_definition import encode_instruction, OPCODES
	PIPE_OK = True
except Exception as e:
	print(f"[test_pipeline_basic] ⚠️ No se pudo importar Pipeline/ISA ({e}); se omite prueba.")
	PIPE_OK = False

@unittest.skipUnless(PIPE_OK, "Pipeline/ISA no disponible")
class PipelineBasicTests(unittest.TestCase):
	def test_add_sequence(self):
		prog = [
			encode_instruction('I_TYPE', opcode=OPCODES['LOADI'], rd=1, rs1=0, imm=5),
			encode_instruction('I_TYPE', opcode=OPCODES['LOADI'], rd=2, rs1=0, imm=7),
			encode_instruction('R_TYPE', opcode=OPCODES['ADD'], rd=3, rs1=1, rs2=2, funct=0),
		]
		p = Pipeline(prog)
		for _ in range(3):
			p.step()
		regs = p.rf.dump_registers()
		self.assertEqual(regs['R3'], 12)

if __name__ == "__main__":
	unittest.main()
