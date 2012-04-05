#!/usr/bin/env python

"""
A simple Forth compiler for Notch's CPU.

J is used as a scratchpad. When necessary, so is I.

SP is used for the main stack. X is used for the call stack.

At the end of the program, the stack is popped into I and J for analysis.
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


def trampoline(address):
    """
    Jump to an absolute address. Always two words.
    """

    return pack(">HH", 0x7dc1, address)


def switch_to_call():
    """
    Switch to the call stack.

    You'd better be calling if you do this!
    """

    ucode = assemble(SET, J, SP)
    ucode += assemble(SET, SP, X)
    return ucode


def switch_to_main():
    """
    Switch to the main stack.
    """

    ucode = assemble(SET, X, SP)
    ucode += assemble(SET, SP, J)
    return ucode


def call(target, ret):
    """
    Call a subroutine.

    Safety not guaranteed; you might not ever come back.
    """

    ucode = switch_to_call()
    ucode += assemble(SET, PUSH, ret)
    ucode += assemble(SET, PC, target)
    return ucode


def ret():
    """
    Return to the caller.

    It's totally possible to return to lala-land if overused.
    """

    ucode = switch_to_call()
    ucode += assemble(SET, PC, POP)
    return ucode


def bootloader(start):
    """
    Set up stacks and registers, and then jump to a starting point. After
    things are finished, pop some of the stack to registers, and halt with an
    illegal opcode.
    """

    # First things first. Set up the call stack. Currently hardcoded.
    ucode = assemble(SET, X, 0xd000)
    # Hardcode the location of the tail, and call.
    ucode += call(start, 0x6)
    # And we're off! As soon as we come back down...
    ucode += switch_to_main()
    ucode += tail()
    # Finish off with an illegal opcode.
    ucode += pack(">H", 0x0)
    return ucode


def subroutine(name, words, pc, context):
    """
    Compile a list of words into a new word and add it to the context.

    All subroutines, including main, are called into; thus they assume that
    the current stack is the call stack and switch out of it before doing any
    work. They switch back to the call stack when returning.
    """

    ucode = switch_to_main()

    for word in words:
        if word in context:
            # Compile a call.
            # The amount of space required ahead of this call.
            space = 0x6
            ucode += call(context[word][0], pc + len(ucode) + space)
            # Switch back to main stack.
            ucode += switch_to_main()
        else:
            ucode += builtin(word)

    ucode += ret()

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

    if word == "-":
        ucode = assemble(SET, J, POP)
        ucode += assemble(SUB, PEEK, J)
        return ucode

    raise Exception("Don't know builtin %r" % word)


with open("test.forth", "rb") as f:
    tokens = [t.strip() for t in f.read().split()]
    pc = len(bootloader(0)) // 2
    context = {}
    while tokens:
        t, tokens = tokens[0], tokens[1:]
        if t == ":":
            name = tokens[0]
            end = tokens.index(";")
            sub = subroutine(name, tokens[1:end], pc, context)
            # Add the size of the subroutine to PC.
            pc += len(sub) // 2


with open("test.bin", "wb") as f:
    start = context["main"][0]
    boot = bootloader(start)
    print "Bootloader: %d bytes (%d words)" % (len(boot), len(boot) // 2)
    f.write(boot)
    for name in context:
        pc, u = context[name]
        print "Sub %s: %d bytes (%d words) @ 0x%x" % (name, len(u),
            len(u) // 2, pc)
        f.seek(pc)
        f.write(u)
