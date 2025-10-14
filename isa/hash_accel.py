#hash_accel.py

"""
Implementaciones de referencia para operaciones de mezcla/hash (ToyMDMA).
Aviso: son funciones de referencia y NO deben considerarse seguras
cryptográficamente; sirven para pruebas e integración del pipeline.
Funciones principales:
 - mixmul(a, b): mezcla y multiplica (trunca a 64 bits)
 - modadd(a, b): suma con reducción modular usando PRIMO_MOD por defecto
 - nonlin(x): función no lineal determinista
 - apply_block(state, block): aplica un bloque sobre Vec4x64
"""
from .isa_types import UInt64, Vec4x64
from .isa_definition import TOYMDMA_CONSTANTS

MASK64 = 0xFFFFFFFFFFFFFFFF

def mixmul(a: int, b: int) -> UInt64:
    """Mezcla y multiplica: ( (a XOR GOLDEN_RATIO) * b ) mod 2^64"""
    gr = TOYMDMA_CONSTANTS['GOLDEN_RATIO']
    res = ((a ^ gr) * b) & MASK64
    return UInt64(res)

def modadd(a: int, b: int, mod: int = None) -> UInt64:
    """Suma con reducción modular usando PRIME_MOD por defecto (si se especifica)."""
    if mod is None:
        mod = TOYMDMA_CONSTANTS['PRIME_MOD']
    res = (int(a) + int(b)) % int(mod)
    return UInt64(res)

def nonlin(x: int) -> UInt64:
    """Operación no lineal simple: rotl(x,13) XOR (x * GOLDEN_RATIO)"""
    val = int(x) & MASK64
    rot = ((val << 13) & MASK64) | (val >> (64 - 13))
    res = (rot ^ ((val * TOYMDMA_CONSTANTS['GOLDEN_RATIO']) & MASK64)) & MASK64
    return UInt64(res)

def apply_block(state: Vec4x64, block: int) -> Vec4x64:
    """
    Aplica un bloque al estado hash.
    - state: Vec4x64 (A,B,C,D)
    - block: 64-bit integer (mensaje)
    Devuelve un nuevo Vec4x64 con las actualizaciones.
    """
    A = state[0]
    B = state[1]
    C = state[2]
    D = state[3]
    m = UInt64(block & MASK64)

    # Mezclas y operaciones inspiradas en el enunciado (no criptográficamente formales)
    t1 = mixmul(int(A), int(m))
    t2 = modadd(int(B), int(t1))
    t3 = nonlin(int(C) ^ int(m))
    t4 = mixmul(int(D) ^ int(t2), TOYMDMA_CONSTANTS['GOLDEN_RATIO'] & MASK64)

    newA = UInt64(int(t1) ^ int(t4))
    newB = UInt64(int(t2) + int(t3))
    newC = UInt64(int(t3) ^ int(newA))
    newD = UInt64(int(t4) + int(newB))

    return Vec4x64(newA, newB, newC, newD)
