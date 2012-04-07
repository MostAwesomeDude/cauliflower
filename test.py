#!/usr/bin/env python

"""
A simple Forth compiler for Notch's CPU.

The main data stack lives in SP, always. PUSH and POP are the preferred
methods of operating on the stack.

The return/call stack is hacked onto Z. Explicit manipulations are done to
modify Z.

At the end of the program, the stack is popped into I and J for analysis.
"""

from collections import OrderedDict
from struct import pack
import sys

from cauliflower.assembler import I, J, POP, SET, Z, assemble
from cauliflower.builtins import builtin
from cauliflower.control import call, if_alone, if_else, ret


# The threshold of inlining. Words that are compiled to this many machine
# words of bytecode or fewer will not be inserted as callable subroutines into
# the executable, but instead will join a library of builtin subroutines which
# will be added verbatim whenever called. This is largely because calls can be
# very expensive and composite words can be very small.
# Currently, this threshold is set to eight words, the overhead of a call()
# plus the ret() cost at the end of a subroutine, times two, the size of a
# word.
INLINING_THRESHOLD = 0x8 * 2


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
        # We've seen this word before, so either compile a call to it or
        # include it verbatim if it's inlined.
        pc, ucode = context[word]
        if pc is None:
            return ucode
        else:
            return call(pc)
    else:
        # Haven't seen this word, maybe it's a builtin?
        return builtin(word)


def compile_if(name, count, words, pc, context):
    """
    Find an if statement, compile one or two blocks of it, and return the
    pieces.
    """

    print "Compiling if", name, count, words, pc, context

    if_clause = []
    else_clause = []
    else_pc = None

    it = iter(words)
    word = next(it)
    while word not in ("else", "then"):
        if_clause.append(word)
        word = next(it)
    print "If clause:", if_clause
    if_pc = pc
    pc = subroutine("%s_if_%d" % (name, count), if_clause, pc, context)

    if word == "else":
        word = next(it)
        while word != "then":
            else_clause.append(word)
            word = next(it)
        print "Else clause:", else_clause
        else_pc = pc
        pc = subroutine("%s_else_%d" % (name, count), else_clause, pc,
                        context)

    return count, if_pc, else_pc, pc


def subroutine(name, words, pc, context):
    """
    Compile a list of words into a new word.

    All subroutines, including main, are called into.

    If None is returned, then the new word is inline.
    """

    ucode = []
    it = iter(words)
    ifs = 0

    force_inline = False

    for word in it:
        if word == "inline":
            force_inline = True
        if word == "if":
            ifs, ifpc, elsepc, pc = compile_if(name, ifs, it, pc, context)
            print "Compiled if", ifs, ifpc, elsepc
            print "PC is currently", pc
            if elsepc is None:
                ucode.append(if_alone(ifpc))
            else:
                ucode.append(if_else(ifpc, elsepc))
        else:
            ucode.append(compile_word(word, context))

    ucode = "".join(ucode)
    inline = force_inline or len(ucode) <= INLINING_THRESHOLD

    if inline:
        # Add to the dictionary with pc == None, to indicate that this word
        # can't be found in the emitted bytecode.
        context[name] = None, ucode
    else:
        # This routine can be found in the bytecode, so it needs to return
        # after call.
        ucode += ret()
        # Add the word to the dictionary.
        context[name] = pc, ucode
        # Add the size of the subroutine to PC.
        pc += len(ucode) // 2

    return pc


def compile_tokens(tokens, pc, context):
    """
    Compile some tokens and add any new words to the given context.

    Returns the PC corresponding to the end of the context.
    """

    it = iter(tokens)
    ignore = False
    subtokens = None

    for token in it:
        # Handle comments. Whether or not a Forth permits nested comments is
        # pretty up-in-the-air; this Forth does not permit nesting of
        # comments.
        if token == "(":
            ignore = True
            continue
        elif token == ")":
            ignore = False
            continue

        if ignore:
            continue

        # Look for subroutines.
        if token == ":":
            subtokens = []
            continue
        elif token == ";":
            if not subtokens:
                raise Exception("Empty word definition!")
            name = subtokens[0]
            pc = subroutine(name, subtokens[1:], pc, context)
            continue
        elif subtokens is not None:
            subtokens.append(token)
            continue

        raise Exception("Lone word %r in tokenizer!" % token)

    return pc


with open("prelude.forth", "rb") as f:
    tokens = [t.strip().lower() for t in f.read().split()]
    pc = len(bootloader(0)) // 2 + 1
    context = OrderedDict()
    pc = compile_tokens(tokens, pc, context)


with open(sys.argv[1], "rb") as f:
    tokens = [t.strip().lower() for t in f.read().split()]
    pc = compile_tokens(tokens, pc, context)


with open(sys.argv[2], "wb") as f:
    start = context["main"][0]
    boot = bootloader(start)
    print "Bootloader: %d bytes (%d words)" % (len(boot), len(boot) // 2)
    f.write(boot)
    for name in context:
        pc, u = context[name]
        if pc is None:
            print "Word %s: %d bytes (%d words) (inline)" % (name, len(u),
                len(u) // 2)
            continue

        print "Sub %s: %d bytes (%d words) @ 0x%x" % (name, len(u),
            len(u) // 2, pc)
        f.seek(pc * 2)
        f.write(u)
