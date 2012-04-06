#!/usr/bin/env python

"""
A simple Forth compiler for Notch's CPU.

The main data stack lives in SP, always. PUSH and POP are the preferred
methods of operating on the stack.

The return/call stack is hacked onto Z. Explicit manipulations are done to
modify Z.

At the end of the program, the stack is popped into I and J for analysis.

Like many Forths, this Forth does not support mutual recursion; words must be
fully defined before they can be used.
"""

from struct import pack
import sys

from cauliflower.assembler import I, J, POP, SET, Z, assemble
from cauliflower.builtins import builtin
from cauliflower.control import call, ret


def bootloader(start):
    """
    Set up stacks and registers, and then jump to a starting point. After
    things are finished, pop some of the stack to registers, and halt with an
    illegal opcode.
    """

    # First things first. Set up the call stack. Currently hardcoded.
    ucode = assemble(SET, Z, 0xd000)
    # Hardcode the location of the tail, and call.
    ucode += call(start)
    # And we're off! As soon as we come back down, pop I and J so we can see
    # them easily.
    ucode += assemble(SET, I, POP)
    ucode += assemble(SET, J, POP)
    # Finish off with an illegal opcode.
    ucode += pack(">H", 0x0)
    return ucode


def compile_word(word, context):
    """
    Compile a single word.
    """

    if word in context:
        # We've seen this word before, so compile a call to it.
        return call(context[word][0])
    else:
        # Haven't seen this word, maybe it's a builtin?
        return builtin(word)


def subroutine(name, words, pc, context):
    """
    Compile a list of words into a new word and add it to the context.

    All subroutines, including main, are called into.
    """

    ucode = []

    for word in words:
        ucode.append(compile_word(word, context))

    ucode.append(ret())

    ucode = "".join(ucode)

    context[name] = pc, ucode
    return ucode


with open("prelude.forth", "rb") as f:
    tokens = [t.strip().lower() for t in f.read().split()]
    pc = len(bootloader(0)) // 2 + 1
    context = {}
    it = iter(tokens)
    for token in it:
        if token == ":":
            name = next(it)
            subtokens = []
            while token != ";":
                token = next(it)
                subtokens.append(token)
            sub = subroutine(name, subtokens, pc, context)
            # Add the size of the subroutine to PC.
            pc += len(sub) // 2


with open(sys.argv[1], "rb") as f:
    tokens = [t.strip().lower() for t in f.read().split()]
    it = iter(tokens)
    for token in it:
        if token == ":":
            name = next(it)
            subtokens = []
            while token != ";":
                token = next(it)
                subtokens.append(token)
            sub = subroutine(name, subtokens, pc, context)
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
