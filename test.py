#!/usr/bin/env python

from struct import pack

SET, ADD, SUB, MUL, DIV, MOD, SHL, SHR, AND, BOR, XOR, IFE, IFN, IFG, IFB = range(1, 16)

binops = range(1, 16)

A, B, C, X, Y, Z, I, J = range(8)
POP, PEEK, PUSH, SP, PC, O = range(24, 30)

registers = range(8)
direct_registers = registers + range(24, 30)

def value(v):
    """
    Return a binary value corresponding to the given value object.

    A list around a value is an indirection; a tuple is a literal.

    A tuple of one or two words will be returned; a second word indicates an
    extended-size instruction with a trailing literal.
    """

    if v in direct_registers:
        # Register
        return v,
    elif isinstance(v, list):
        iv, = v
        if iv in registers:
            # Indirect register
            return iv + 0x8,
        else:
            # Extended indirection
            return 0x1e, iv
    elif isinstance(v, tuple):
        v, = v
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

data = [
    assemble(SET, A, (0x30,)),
    assemble(SET, [0x1000], (0x20,)),
]

with open("test.bin", "wb") as f:
    f.write("".join(data))
