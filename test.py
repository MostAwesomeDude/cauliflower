#!/usr/bin/env python

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

data = [
    assemble(SET, A, 0x30),
    assemble(SET, [0x1000], 0x20),
    assemble(SUB, A, [0x1000]),
    assemble(IFN, A, 0x10),
]

def trampoline(address):
    """
    Jump to an address. Always two words.
    """

    return pack(">HH", 0x7dc1, address)

def subroutine(name, words, pc, context):
    """
    Compile a list of words into a new word and add it to the context.
    """

    ucode = ""

    for word in words:
        if word in context:
            # Compile a call.
            pass
        else:
            ucode += builtin(word)

    context[name] = pc, ucode
    return ucode

def tail():
    """
    Pop the stack into I and J so that we can see what's been done.
    """

    ucode = assemble(SET, I, POP)
    ucode += assemble(SET, J, POP)
    return ucode

def builtin(word):
    """
    Compile a builtin word.
    """

    try:
        i = int(word)
        ucode = assemble(SET, PUSH, i)
        return ucode
    except ValueError:
        pass

    if word == "+":
        ucode = assemble(SET, J, POP)
        ucode += assemble(ADD, PEEK, J)
        return ucode

    raise Exception("Don't know builtin %r" % word)

with open("test.forth", "rb") as f:
    tokens = [t.strip() for t in f.read().split()]
    pc = 0x2
    context = {}
    while tokens:
        t, tokens = tokens[0], tokens[1:]
        if t == ":":
            name = tokens[0]
            end = tokens.index(";")
            sub = subroutine(name, tokens[1:end], pc, context)
            # Increment PC times 2 for the word size.
            pc += len(sub) * 2
            if name == "main":
                # Leave space for a trampoline which we will use to reach the
                # end of the program.
                pc += 0x2

with open("test.bin", "wb") as f:
    start = context["main"][0]
    f.write(trampoline(start))
    for name in context:
        pc, u = context[name]
        f.write(u)
        if name == "main":
            # Set the end-of-program trampoline.
            address = pc + len(u)
    target = f.tell() // 2
    f.write(tail())
    tramp = trampoline(target)
    f.seek(address * 2)
    f.write(tramp)
