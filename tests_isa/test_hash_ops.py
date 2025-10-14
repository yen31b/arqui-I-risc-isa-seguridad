import os, sys, unittest
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
	sys.path.append(ROOT)

try:
	from isa.hash_accel import mixmul, modadd, nonlin, apply_block
	from isa.isa_types import Vec4x64
	ACCEL_AVAILABLE = True
except Exception as e:
	print(f"[test_hash_ops] ⚠️ No se pudo importar hash_accel ({e}); se omiten pruebas.")
	ACCEL_AVAILABLE = False

@unittest.skipUnless(ACCEL_AVAILABLE, "hash_accel no disponible")
class HashOpsTests(unittest.TestCase):
	def test_mixmul_nonlin_modadd(self):
		a, b = 0x1234, 0xFEDC
		self.assertIsNotNone(mixmul(a, b))
		self.assertEqual(int(modadd(10, 5, mod=13)), (10+5) % 13)
		self.assertIsNotNone(nonlin(0xCAFEBABE))

	def test_apply_block_changes_state(self):
		state = Vec4x64([1,2,3,4])
		new_state = apply_block(state, 0xA5A5A5A5A5A5A5A5)
		# Vec4x64 puede no implementar __len__; validamos por indexación
		new_vals = [int(new_state[i]) for i in range(4)]
		old_vals = [int(state[i]) for i in range(4)]
		self.assertEqual(len(new_vals), 4)
		self.assertNotEqual(old_vals, new_vals)

if __name__ == "__main__":
	unittest.main()
