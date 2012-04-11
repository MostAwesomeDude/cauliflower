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

from cauliflower.assembler import (A, ADD, B, C, I, IFE, IFN, J, JSR, PEEK,
                                   PC, POP, PUSH, SET, SP, SUB, X, Y, Z,
                                   assemble, until)
from cauliflower.utilities import memcmp


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

    # Address of memcmp.
    memcmp = 0x0

    # Workspace address.
    workspace = 0x7000


    def __init__(self):
        self.space = StringIO()
        self.bootloader()

        # Set up NEXT.
        self.NEXT = self.space.tell() // 2
        self.space.write(NEXT())

        # Set up memcmp.
        self.memcmp = self.space.tell() // 2
        self.space.write(memcmp())

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


    def create(self, name):
        """
        Write a header into the core and update the previous header marker.
        """

        location = self.space.tell() // 2

        self.space.write(pack(">HH", self.previous, len(name)))
        self.space.write(name.encode("utf-16-be"))

        self.previous = location


    def finish(self, name):
        """
        Finish writing a word or thread.
        """

        self.space.write(EXIT())
        self.space.write(assemble(SET, PC, self.NEXT))
        self.codewords[name] = self.previous


    def asm(self, name, ucode):
        """
        Write an assembly-level word into the core.

        Here's what the word looks like:

        |prev|len |name|asm |EXIT|
        """

        print "Adding assembly word %s" % name

        self.create(name)
        self.space.write(ucode)
        self.finish(name)


    def thread(self, name, words):
        """
        Assemble a thread of words into the core.

        Here's what a thread looks like:

        |prev|len |name|word|EXIT|
        """

        print "Adding Forth thread %s" % name

        self.create(name)
        self.space.write(ENTER())
        for word in words:
            if isinstance(word, int):
                self.space.write(pack(">H", word))
            elif word in self.codewords:
                self.space.write(self.codewords[word])
            else:
                raise Exception("Can't reference unknown word %r" % word)
        self.finish(name)


ma = MetaAssembler()

# Compiling words.

ucode = _push([J])
ucode += assemble(ADD, J, 0x1)
ma.asm("literal", ucode)

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

# Main stack manipulation.

ucode = assemble(SET, PUSH, Z)
ma.asm("dup", ucode)

# Return stack manipulation.

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

ma.thread("key", ["literal", 0x7fff, "@"])

# Top of the line: Go back to the beginning of the string.
ucode = assemble(SET, X, 0x0)
# Read a character from the keyboard.
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
ucode += assemble(JSR, ma.memcmp)
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
ma.asm("find", ucode)

ma.thread(">cfa", ["literal", 0x1, "+", "dup", "@", "+", "literal", 0x1, "+"])
