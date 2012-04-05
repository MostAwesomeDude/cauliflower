#!/usr/bin/env python

"""
A simple Forth compiler for Notch's CPU.

J is used as a scratchpad. When necessary, so is I.

X is used for the main stack. Y is used for the call stack. The active stack
is on SP.

At the end of the program, the stack is popped into I and J for analysis.
"""

from cauliflower.assembler import *
from cauliflower.builtins import builtin

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

    ucode = assemble(SET, X, SP)
    ucode += assemble(SET, SP, Y)
    return ucode


def switch_to_main():
    """
    Switch to the main stack.
    """

    ucode = assemble(SET, Y, SP)
    ucode += assemble(SET, SP, X)
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
    ucode = assemble(SET, Y, 0xd000)
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


with open("test.forth", "rb") as f:
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


with open("test.bin", "wb") as f:
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
