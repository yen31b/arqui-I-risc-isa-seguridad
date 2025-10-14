# current_test.py
import sys
import os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.append(ROOT)

import traceback
from isa.register_file import register_file
from isa.isa_types import UInt64, Vec4x64
from isa.isa_definition import VAULT_SLOTS, OPCODES, encode_instruction, get_field_value, instruction_to_string
from vault.vault import KeyVault, VaultAccessError
from isa import addressing_modes as addr_modes
from isa.hash_accel import mixmul, modadd, nonlin, apply_block

def _run_and_report(name, fn):
    print("\n" + "-" * 70)
    print(f" START: {name}")
    print("-" * 70)
    try:
        fn()
        print(f" END  : {name} -> PASSED")
        return True, None
    except AssertionError as ae:
        print(f" END  : {name} -> FAILED (Assertion): {ae}")
        traceback.print_exc(limit=1)
        return False, ae
    except Exception as e:
        print(f" END  : {name} -> ERROR: {e}")
        traceback.print_exc()
        return False, e

# ---------------- Vault / SGEN tests ----------------
def vault_tests():
    def t1():
        kv = KeyVault()
        print("Slots (expected keys):", list(VAULT_SLOTS.keys()))
        dump0 = kv.dump_vault(authorized=True)
        print("Initial dump (expected all None):", dump0)
        assert all(v is None for v in dump0.values())

        kv.write_slot('KEY_0', 0xDEADBEEFCAFEBABE, authorized=True)
        dump1 = kv.dump_vault(authorized=True)
        print("After write dump:", dump1)
        assert dump1['KEY_0'] == 0xDEADBEEFCAFEBABE

    def t2():
        kv = KeyVault()
        try:
            kv.write_slot('KEY_1', 0x1, authorized=False)
            raise AssertionError("Expected VaultAccessError")
        except VaultAccessError:
            print("Unauthorized write correctly raised VaultAccessError")

    def t3():
        kv = KeyVault()
        kv.write_slot('KEY_0', 0xA5A5A5A5A5A5A5A5, authorized=True)
        # Compatibilidad: usar API disponible
        if hasattr(kv, 'access_slot_for_operation'):
            val = kv.access_slot_for_operation('KEY_0', 'KVL')
            ival = int(val)
        else:
            ival = int(kv.get_handle('KEY_0', 'KVL').xor_scalar(0))
        print("Access returned (int):", hex(int(ival)))
        assert int(ival) == 0xA5A5A5A5A5A5A5A5
        try:
            if hasattr(kv, 'access_slot_for_operation'):
                kv.access_slot_for_operation('KEY_0', 'BAD_OP')
            else:
                kv.get_handle('KEY_0', 'BAD_OP')
            raise AssertionError("Expected VaultAccessError for BAD_OP")
        except VaultAccessError:
            print("Bad op correctly blocked")

    def t4():
        kv = KeyVault()
        key = 0xFF00FF00FF00FF00
        kv.write_slot('KEY_0', key, authorized=True)
        st = Vec4x64([UInt64(1), UInt64(2), UInt64(3), UInt64(4)])
        sig = kv.generate_signature('KEY_0', st)
        expected = Vec4x64([UInt64(int(st[i]) ^ key) for i in range(4)])
        print("State   :", [hex(int(st[i])) for i in range(4)])
        print("Key     :", hex(key))
        print("Expected:", [hex(int(expected[i])) for i in range(4)])
        print("Obtained:", [hex(int(sig[i])) for i in range(4)])
        assert [int(sig[i]) for i in range(4)] == [int(expected[i]) for i in range(4)]

    return [("Vault.write_authorized", t1),
            ("Vault.write_unauthorized", t2),
            ("Vault.access_ops", t3),
            ("Vault.generate_signature", t4)]

# ---------------- HashAccel tests ----------------
def hash_tests():
    MASK64 = 0xFFFFFFFFFFFFFFFF

    def th1():
        a, b = 0x2, 0x3
        gr = 0x9e3779b97f4a7c15
        expected = ((a ^ gr) * b) & MASK64
        res = mixmul(a, b)
        print(f"mixmul inputs a={hex(a)} b={hex(b)} golden={hex(gr)}")
        print("expected:", hex(expected), "obtained:", hex(int(res)))
        assert int(res) == expected

    def th2():
        a, b = 5, 7
        mod = 0xFFFFFFFB
        expected = (a + b) % mod
        res = modadd(a, b)
        print("modadd expected:", expected, "obtained:", int(res))
        assert int(res) == expected

    def th3():
        x = 0x123456789ABCDEF0
        r1 = nonlin(x); r2 = nonlin(x)
        print("nonlin inputs:", hex(x), "outputs:", hex(int(r1)), hex(int(r2)))
        assert int(r1) == int(r2)

    def th4():
        st = Vec4x64(0x1, 0x2, 0x3, 0x4)
        new = apply_block(st, 0xCAFEBABEDEADBEEF)
        print("apply_block state:", [hex(int(st[i])) for i in range(4)])
        print("apply_block new  :", [hex(int(new[i])) for i in range(4)])
        assert isinstance(new, Vec4x64)
        assert any(int(new[i]) != int(st[i]) for i in range(4))

    return [("Hash.mixmul", th1),
            ("Hash.modadd", th2),
            ("Hash.nonlin", th3),
            ("Hash.apply_block", th4)]

# ---------------- RegisterFile tests ----------------
def register_tests():
    def tr1():
        rf = register_file()
        rf.write('R5', 0x123456789ABCDEF0)
        v = rf.read('R5')
        print("R5 expected:", hex(0x123456789ABCDEF0), "got:", hex(int(v)))
        assert int(v) == 0x123456789ABCDEF0

    def tr2():
        rf = register_file()
        rf.write('PC', 0x1000); rf.write('SR', 0xDEAD)
        print("PC:", hex(int(rf.read('PC'))), "SR:", hex(int(rf.read('SR'))))
        assert int(rf.read('PC')) == 0x1000
        assert int(rf.read('SR')) == 0xDEAD

    def tr3():
        rf = register_file()
        rf.write('R1', 0x1FFFFFFFFFFFFFFFF)
        v = rf.read('R1')
        print("Masking expected 0xFFFFFFFFFFFFFFFF got:", hex(int(v)))
        assert int(v) == 0xFFFFFFFFFFFFFFFF

    def tr4():
        rf = register_file()
        try:
            rf.write('R32', 1)
            raise AssertionError("Expected ValueError")
        except ValueError:
            print("Invalid write correctly raised ValueError")
        try:
            rf.read('R32')
            raise AssertionError("Expected ValueError")
        except ValueError:
            print("Invalid read correctly raised ValueError")

    return [("Regs.write_read", tr1),
            ("Regs.specials", tr2),
            ("Regs.masking", tr3),
            ("Regs.invalid_access", tr4)]

# ---------------- Addressing modes tests ----------------
def addressing_tests():
    def ta1():
        rf = register_file()
        rf.write('R1', 0x100)
        addr = addr_modes.mode_REG(rf, 'R1')
        print("mode_REG addr expected 0x100 got", hex(int(addr)))
        assert int(addr) == 0x100

    def ta2():
        rf = register_file()
        rf.write('R2', 0x200)
        addr = addr_modes.mode_REG_IMM(rf, 'R2', 0x10)
        print("mode_REG_IMM expected 0x210 got", hex(int(addr)))
        assert int(addr) == 0x200 + (0x10 & 0xFFFF)

    def ta3():
        rf = register_file()
        rf.write('R3', 0x300)
        rf.write('R4', 0x40)
        addr = addr_modes.mode_BASE_DISP(rf, 'R3', 'R4')
        print("mode_BASE_DISP expected 0x340 got", hex(int(addr)))
        assert int(addr) == 0x300 + 0x40

    def ta4():
        addr = addr_modes.mode_IMM_LONG(0xDEADBEAFDEAD)
        print("mode_IMM_LONG got", hex(int(addr)))
        assert int(addr) == (0xDEADBEAFDEAD & 0xFFFFFFFFFFFFFFFF)

    def ta5():
        try:
            addr_modes.validate_address(0x5, vault_range=(0, 0x10))
            raise AssertionError("Expected PermissionError")
        except PermissionError:
            print("validate_address correctly blocked vault-range access")

    return [("Addr.REG", ta1),
            ("Addr.REG_IMM", ta2),
            ("Addr.BASE_DISP", ta3),
            ("Addr.IMM_LONG", ta4),
            ("Addr.validate_vault_range", ta5)]

# ---------------- Encoding/Decoding tests ----------------
def encoding_tests():
    def te1():
        opcode = OPCODES['ADD']
        instr = encode_instruction('R_TYPE', opcode=opcode, rd=1, rs1=2, rs2=3, funct=0)
        got_opcode = get_field_value(instr, 'opcode', 'R_TYPE')
        print("Encoded instr:", hex(instr))
        print("Extracted opcode expected", bin(opcode), "got", bin(got_opcode))
        assert got_opcode == opcode
        print("instruction_to_string:", instruction_to_string(instr))
    return [("Encode.R_TYPE_roundtrip", te1)]

# ---------------- Runner ----------------
if __name__ == "__main__":
    sections = [
        ("Bóveda / SGEN", vault_tests()),
        ("Hash Accelerator", hash_tests()),
        ("Register File", register_tests()),
        ("Addressing Modes", addressing_tests()),
        ("Encoding/Decoding", encoding_tests()),
    ]

    total = 0
    passed = 0
    failures = []

    for section_name, tests in sections:
        print("\n" + "=" * 80)
        print(f" SECTION: {section_name}")
        print("=" * 80)
        for name, fn in tests:
            total += 1
            ok, ex = _run_and_report(f"{section_name}::{name}", fn)
            if ok:
                passed += 1
            else:
                failures.append((f"{section_name}::{name}", ex))

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total tests attempted: {total}")
    print(f"Passed: {passed}")
    print(f"Failed/Errored: {len(failures)}")
    if failures:
        print("\nFailures details:")
        for n, e in failures:
            print(f"- {n}: {e}")
    else:
        print("All tests passed.")