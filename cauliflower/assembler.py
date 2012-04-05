"""
An assembler for Notch's CPU.
"""

from struct import pack

(SET, ADD, SUB, MUL, DIV, MOD, SHL, SHR, AND, BOR, XOR, IFE, IFN, IFG, IFB
) = range(1, 16)

binops = range(1, 16)

A, B, C, X, Y, Z, I, J = [object() for chaff in range(8)]
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
    elif isinstance(v, list):
        iv, = v
        if iv in registers:
            # Indirect register
            return rdict[iv] + 0x8,
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