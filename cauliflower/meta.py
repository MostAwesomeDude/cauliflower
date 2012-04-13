"""
The metainterpreter and metabuiltins.

There are seven Forth registers: W, IP, PSP, RSP, X, UP, and TOS. They are
assigned to hardware registers as follows:

+---+--+
|W  |I |
|IP |J |
|PSP|SP|
|RSP|Y |
|X  |X |
|UP |C |
|TOS|Z |
+---+--+

To start the metainterpreter, set RSP to point to a safe area of return stack,
put the address of QUIT into IP, and then call IP.
"""

from StringIO import StringIO
from struct import pack

from cauliflower.assembler import (A, ADD, B, BOR, C, I, IFE, IFN, J, PEEK,
                                   PC, POP, PUSH, SET, SP, SUB, X, XOR, Y, Z,
                                   assemble, call, until)
from cauliflower.utilities import library, read


IMMEDIATE = 0x4000
HIDDEN = 0x8000


def NEXT():
    """
    Increment IP and jump to the address which it contains.
    """
    ucode = assemble(ADD, J, 0x1)
    ucode += assemble(SET, PC, J)
    return ucode


def PUSHRSP(register):
    """
    Push onto RSP.
    """
    ucode = assemble(SUB, Y, 0x1)
    ucode += assemble(SET, [Y], register)
    return ucode


def POPRSP(register):
    """
    Pop from RSP.
    """
    ucode = assemble(SET, register, [Y])
    ucode += assemble(ADD, Y, 0x1)
    return ucode


def ENTER():
    """
    Push IP onto RSP, increment W, move W to IP, and call NEXT.

    Sometimes called DOCOL.
    """
    ucode = PUSHRSP(J)
    ucode += assemble(ADD, I, 0x1)
    ucode += assemble(SET, J, I)
    ucode += NEXT()
    return ucode


def EXIT():
    """
    Pop RSP into IP.
    """
    ucode = POPRSP(J)
    return ucode


def _push(register):
    """
    Push onto the stack, manipulating both TOS and PSP.
    """
    ucode = assemble(SET, PUSH, Z)
    ucode += assemble(SET, Z, register)
    return ucode


def _pop(register):
    """
    Pop off the stack, manipulating both TOS and PSP.
    """
    ucode = assemble(SET, register, Z)
    ucode += assemble(SET, Z, POP)
    return ucode


class MetaAssembler(object):
    """
    Assembler which pulls threads together to form a Forth core.
    """

    # Pointer to the previous word defined, used to chain all words onto a
    # linked list.
    previous = 0x0

    # Address of NEXT. NEXT isn't contained in a thread and hopefully is close
    # enough to the top of address space that it can be jumped to with a short
    # literal instead of a long literal.
    NEXT = 0x0

    # Workspace address.
    workspace = 0x7000


    def __init__(self):
        self.space = StringIO()
        self.bootloader()

        # Set up NEXT.
        self.NEXT = self.space.tell() // 2
        self.space.write(NEXT())

        self.lib()

        # Hold codewords for threads as we store them.
        self.codewords = {}


    def bootloader(self):
        """
        Set up the bootloader.
        """

        self.space.write(assemble(SET, Y, 0xd000))
        # XXX this would push QUIT and jump, at some point.
        self.space.write("\x00" *  2 * 3)

        # Allocate space for STATE.
        self.STATE = self.space.tell()
        self.space.write("\x00\x00")

        # And HERE.
        self.HERE = self.space.tell()
        self.space.write("\x00\x00")

        # And LATEST, too.
        self.LATEST = self.space.tell()
        self.space.write("\x00\x00")

        # Don't forget BASE.
        self.BASE = self.space.tell()
        self.space.write("\x00\x00")


    def lib(self):
        self.library = {}
        for name in library:
            print "Adding library function", name
            self.library[name] = self.space.tell() // 2
            self.space.write(library[name]())


    def finalize(self):
        # Write HERE and LATEST.
        location = self.space.tell()
        here = pack(">H", location)
        latest = pack(">H", self.previous)
        self.space.seek(self.HERE)
        self.space.write(here)
        self.space.seek(self.LATEST)
        self.space.write(latest)

        # Reset file pointer.
        self.space.seek(location)


    def create(self, name, flags):
        """
        Write a header into the core and update the previous header marker.
        """

        location = self.space.tell() // 2
        length = len(name)
        if flags:
            length |= flags
        header = pack(">HH", self.previous, length)

        self.space.write(header)
        self.space.write(name.encode("utf-16-be"))

        self.previous = location


    def finish(self, name):
        """
        Finish writing a word or thread.
        """

        self.space.write(EXIT())
        self.space.write(assemble(SET, PC, self.NEXT))
        self.codewords[name] = self.previous


    def asm(self, name, ucode, flags=None):
        """
        Write an assembly-level word into the core.

        Here's what the word looks like:

        |prev|len |name|asm |EXIT|
        """

        print "Adding assembly word %s" % name

        self.create(name, flags)
        self.space.write(ucode)
        self.finish(name)


    def thread(self, name, words, flags=None):
        """
        Assemble a thread of words into the core.

        Here's what a thread looks like:

        |prev|len |name|word|EXIT|
        """

        print "Adding Forth thread %s" % name

        self.create(name, flags)
        self.space.write(pack(">H", self.codewords["enter"]))
        for word in words:
            if isinstance(word, int):
                self.space.write(pack(">H", word))
            elif word in self.codewords:
                self.space.write(pack(">H", self.codewords[word]))
            else:
                raise Exception("Can't reference unknown word %r" % word)
        self.finish(name)


ma = MetaAssembler()

# Compiling words.

ucode = ENTER()
ma.asm("enter", ucode)

ucode = EXIT()
ma.asm("exit", ucode)

ucode = _push([J])
ucode += assemble(ADD, J, 0x1)
ma.asm("literal", ucode)
ma.asm("'", ucode)

# Low-level memory manipulation.

ucode = assemble(SET, [Z], PEEK)
# Move the stack back, and then pop the next word into TOS.
ucode += assemble(ADD, SP, 0x1)
ucode += _pop(Z)
ma.asm("!", ucode)

# TOS lets us cheat hard.
ucode = assemble(SET, Z, [Z])
ma.asm("@", ucode)

ucode = assemble(ADD, [Z], PEEK)
# Move the stack back, and then pop the next word into TOS.
ucode += assemble(ADD, SP, 0x1)
ucode += _pop(Z)
ma.asm("+!", ucode)

ucode = assemble(SUB, [Z], PEEK)
# Move the stack back, and then pop the next word into TOS.
ucode += assemble(ADD, SP, 0x1)
ucode += _pop(Z)
ma.asm("-!", ucode)

# Low-level branching.

ucode = assemble(ADD, J, [J])
ma.asm("branch", ucode)

# Ugh.
ucode = assemble(IFN, Z, 0x0)
ucode += assemble(ADD, J, [J])
ucode += assemble(IFE, Z, 0x0)
ucode += assemble(ADD, J, 0x1)
ma.asm("0branch", ucode)

# Goddammit DCPU!
ucode = assemble(SUB, J, [J])
ma.asm("nbranch", ucode)

ucode = assemble(IFN, Z, 0x0)
ucode += assemble(SUB, J, [J])
ucode += assemble(IFE, Z, 0x0)
ucode += assemble(ADD, J, 0x1)
ma.asm("0nbranch", ucode)

# Main stack manipulation.

ucode = assemble(SET, PUSH, Z)
ma.asm("dup", ucode)

# Return stack manipulation.

ucode = _push(0xd000)
ma.asm("r0", ucode)

ucode = _push(Y)
ma.asm("rsp@", ucode)

ucode = _pop(Y)
ma.asm("rsp!", ucode)

ucode = _push([Y])
ucode += assemble(ADD, Y, 0x1)
ma.asm("r>", ucode)

ucode = assemble(SUB, Y, 0x1)
ucode += _pop([Y])
ma.asm(">r", ucode)

ucode = _push([Y])
ma.asm("r@", ucode)

ucode = _pop([Y])
ma.asm("r!", ucode)

ucode = assemble(ADD, Y, 0x1)
ma.asm("rdrop", ucode)

# Arithmetic.

ucode = assemble(ADD, Z, POP)
ma.asm("+", ucode)

# Input.

ucode = assemble(SET, PUSH, Z)
ucode += read(Z)
ma.asm("key", ucode)

# Global access.

# This could be done in Forth, but it's so small in assembly!
ucode = _pop([ma.HERE])
ucode += assemble(ADD, [ma.HERE], 0x1)
ma.asm(",", ucode)

ucode = assemble(SET, [ma.STATE], 0x0)
ma.asm("[", ucode)

ucode = assemble(SET, [ma.STATE], 0x1)
ma.asm("]", ucode)

ucode = _push([ma.LATEST])
ma.asm("latest", ucode)

# Top of the line: Go back to the beginning of the string.
ucode = assemble(SET, X, 0x0)
# Read a character from the keyboard.
ucode += read([X + ma.workspace])
ucode += assemble(SET, [X + ma.workspace], [0x7fff])
ucode += assemble(SET, A, [X + ma.workspace])
ucode += assemble(ADD, X, 0x1)
# If it's a space, then we're done. Otherwise, go back to reading things from
# the keyboard.
ucode = until(ucode, (IFN, 0x20, A))
ucode += _push(ma.workspace)
ucode += _push(X)
ma.asm("word", ucode)

# Pop the target address (below TOS) into a working register. Leave length on
# TOS.
preamble = assemble(SET, A, POP)
# Use B as our linked list pointer.
preamble += assemble(SET, B, ma.LATEST)
# Top of the loop. Dereference B to move along the list.
ucode = assemble(SET, B, [B])
# Compare lengths; if they don't match, go to the next one.
ucode = until(ucode, (IFN, [B + 0x1], Z))
# memcmp() the strings.
ucode += assemble(ADD, B, 0x1)
ucode += assemble(SET, C, A)
ucode += assemble(SET, A, Z)
ucode += call(ma.library["memcmp"])
ucode += assemble(SUB, B, 0x1)
# If it succeeded, push the address back onto the stack and then jump out.
ucode += assemble(IFN, A, 0x0)
ucode += assemble(SET, Z, B)
ucode += assemble(IFN, A, 0x0)
ucode += assemble(ADD, PC, 0x4)
# Loop until we hit NULL.
ucode = until(ucode, (IFE, B, 0x0))
# We finished the loop and couldn't find anything. Guess we'll just set Z to
# 0x0 and exit.
ucode += assemble(SET, Z, 0x0)
ma.asm("find", preamble + ucode)

ma.thread(">cfa", ["literal", 0x1, "+", "dup", "@", "+", "literal", 0x1, "+"])

# Grab HERE. It's going to live in A for a bit.
preamble = assemble(SET, A, [ma.HERE])
# Write LATEST to HERE, update LATEST.
preamble += assemble(SET, [A], [ma.LATEST])
preamble += assemble(SET, [ma.LATEST], A)
# Move ahead, write length.
preamble += assemble(ADD, A, 0x1)
preamble += assemble(SET, [A], Z)
# Set the hidden flag.
preamble += assemble(BOR, [A], HIDDEN)
# SP is nerfed, so grab the source address and put it in B.
preamble += assemble(SET, B, PEEK)
# Loop. Copy from the source address to the target address.
ucode = assemble(SUB, Z, 0x1)
ucode += assemble(SET, [A], [B])
ucode += assemble(ADD, A, 0x1)
ucode += assemble(ADD, B, 0x1)
# Break when we have no more bytes to copy.
ucode = until(ucode, (IFE, Z, 0x0))
# Write out the new HERE.
ucode += assemble(SET, [ma.HERE], A)
# Get the stack to be sane again. Shift it down and then pop, same as 2drop.
ucode += assemble(ADD, SP, 0x1)
ucode += assemble(SET, Z, POP)
ma.asm("create", preamble + ucode)

# The stack points to the top of the header. Move forward one...
ucode = assemble(ADD, Z, 0x1)
# Now XOR in the hidden flag.
ucode += assemble(XOR, [Z], HIDDEN)
# And pop the stack.
ucode += assemble(SET, Z, POP)
ma.asm("hidden", ucode)

# We get to grab LATEST ourselves. On the plus side, no stack touching.
ucode = assemble(SET, A, ma.LATEST)
# XOR that flag!
ucode += assemble(XOR, [A + 0x1], IMMEDIATE)
ma.asm("immediate", ucode)

ma.thread(":", [
    "word",
    "create",
    "literal",
    "enter",
    ",",
    "latest",
    "@",
    "hidden",
    "]",
])

ma.thread(";", [
    "literal",
    "exit",
    ",",
    "latest",
    "@",
    "hidden",
    "[",
], flags=IMMEDIATE)

# ma.thread("quit", ["r0", "rsp!", "interpret", "nbranch", 0x2])

ma.finalize()
