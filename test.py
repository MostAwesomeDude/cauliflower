#!/usr/bin/env python

"""
A simple Forth compiler for Notch's CPU.

The main data stack lives in SP, always. PUSH and POP are the preferred
methods of operating on the stack.

The return/call stack is hacked onto Z. Explicit manipulations are done to
modify Z.

At the end of the program, the stack is popped into I and J for analysis.
"""

import sys

from cauliflower.assembler import *
from cauliflower.builtins import builtin


def call(target, ret):
    """
    Call a subroutine.

    Safety not guaranteed; you might not ever come back.
    """

    ucode = assemble(SUB, Z, 0x1)
    ucode += assemble(SET, [Z], ret)
    ucode += assemble(SET, PC, target)
    return ucode


def ret():
    """
    Return to the caller.

    It's totally possible to return to lala-land...
    """

    return assemble(SET, PC, [Z])


def bootloader(start):
    """
    Set up stacks and registers, and then jump to a starting point. After
    things are finished, pop some of the stack to registers, and halt with an
    illegal opcode.
    """

    # First things first. Set up the call stack. Currently hardcoded.
    ucode = assemble(SET, Z, 0xd000)
    # Hardcode the location of the tail, and call.
    ucode += call(start, 0x5)
    # And we're off! As soon as we come back down...
    ucode += tail()
    # Finish off with an illegal opcode.
    ucode += pack(">H", 0x0)
    return ucode


def subroutine(name, words, pc, context):
    """
    Compile a list of words into a new word and add it to the context.

    All subroutines, including main, are called into.
    """

    ucode = ""

    for word in words:
        if word in context:
            # Compile a call. XXX refactor when references exist.
            c = call(context[word][0], pc + len(ucode))
            # The amount of space required ahead of this call.
            space = len(c)
            ucode += call(context[word][0], pc + len(ucode) + space)
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


with open("prelude.forth", "rb") as f:
    tokens = [t.strip().lower() for t in f.read().split()]
    pc = len(bootloader(0)) // 2 + 1
    context = {}
    while tokens:
        t, tokens = tokens[0], tokens[1:]
        if t == ":":
            name = tokens[0]
            end = tokens.index(";")
            sub = subroutine(name, tokens[1:end], pc, context)
            # Add the size of the subroutine to PC.
            pc += len(sub) // 2


with open(sys.argv[1], "rb") as f:
    tokens = [t.strip().lower() for t in f.read().split()]
    while tokens:
        t, tokens = tokens[0], tokens[1:]
        if t == ":":
            name = tokens[0]
            end = tokens.index(";")
            sub = subroutine(name, tokens[1:end], pc, context)
            # Add the size of the subroutine to PC.
            pc += len(sub) // 2


with open(sys.argv[2], "wb") as f:
    start = context["main"][0]
    boot = bootloader(start)
    print "Bootloader: %d bytes (%d words)" % (len(boot), len(boot) // 2)
    f.write(boot)
    for name in context:
        pc, u = context[name]
        print "Sub %s: %d bytes (%d words) @ 0x%x" % (name, len(u),
            len(u) // 2, pc)
        f.seek(pc * 2)
        f.write(u)
