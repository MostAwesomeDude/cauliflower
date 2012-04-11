"""
An assembler for Notch's CPU.
"""

from collections import namedtuple
from struct import pack

(SET, ADD, SUB, MUL, DIV, MOD, SHL, SHR, AND, BOR, XOR, IFE, IFN, IFG, IFB
) = range(1, 16)

binops = range(1, 16)

Absolute = namedtuple("Absolute", "value")
Offset = namedtuple("Offset", "register, offset")

class Register(object):
    def __add__(self, value):
        return Offset(self, value)

A, B, C, X, Y, Z, I, J = [Register() for chaff in range(8)]
POP, PEEK, PUSH, SP, PC, O = [object() for chaff in range(24, 30)]

rdict = dict((k, v) for k, v in zip([A, B, C, X, Y, Z, I, J], range(8)))
registers = list(rdict.keys())
drdict = dict((k, v)
    for k, v in zip([POP, PEEK, PUSH, SP, PC, O], range(24, 30)))
drdict.update(rdict)
direct_registers = registers + list(drdict.keys())


def value(v):
    """
    Return a binary value corresponding to the given value object.

    A list around a value is an indirection.

    A tuple of one or two words will be returned; a second word indicates an
    extended-size instruction with a trailing literal.
    """

    if v in direct_registers:
        # Register
        return drdict[v],
    elif isinstance(v, Absolute):
        # Inline/extended literal, guaranteed to be extended
        return 0x1f, v.value
    elif isinstance(v, list):
        iv, = v
        if iv in registers:
            # Indirect register
            return rdict[iv] + 0x8,
        elif isinstance(iv, Offset):
            # Indirect register plus offset
            return rdict[iv.register] + 0x10, iv.offset
        else:
            # Extended indirection
            return 0x1e, iv
    elif isinstance(v, int):
        if v < 0x20:
            # Inline literal
            return v + 0x20,
        else:
            # Extended literal
            return 0x1f, v

    raise Exception("Couldn't deal with value %r" % (v,))


def assemble(op, a, b=None):
    """
    Assemble an opcode and return a str of one to three words.
    """

    if op in binops:
        valuea = value(a)
        valueb = value(b)
        n = (valueb[0] << 10) | (valuea[0] << 4) | op
        rv = pack(">H", n)
        if len(valuea) == 2:
            rv += pack(">H", valuea[1])
        if len(valueb) == 2:
            rv += pack(">H", valueb[1])
        return rv

    raise Exception("Couldn't deal with op %r" % (op,))

def until(ucode, condition):
    """
    While a condition fails, repeat a block of instructions. When the
    condition succeeds, the block will be exited by jumping to the next
    instruction at the end of the block.

    The loop is PIC if its contents are also PIC.
    """

    op, a, b = condition
    if op not in (IFB, IFE, IFG, IFN):
        raise Exception("Op %r isn't conditional" % (op,))
    ucode += assemble(op, a, b)
    distance = len(ucode) // 2
    # Compensate for the extra word required to long-jump.
    if distance >= 0x20:
        distance += 1
    ucode += assemble(SUB, PC, distance)

    return ucode
