from cauliflower.assembler import (A, ADD, B, BOR, C, IFE, IFG, IFN, PC, POP,
                                   PUSH, SET, SUB, X, XOR, Y, Z, assemble,
                                   until)

# All of these utility functions expect SP to point to their caller, or at
# least where their caller would like to return to, and assume that SP is safe
# to push onto.

def memcmp():
    """
    Put a length in A, two addresses in B and C, and fill A with whether
    they match (non-zero) or don't match (zero).
    """

    # Save X.
    preamble = assemble(SET, PUSH, X)
    preamble += assemble(SET, X, 0x0)
    preamble += assemble(ADD, B, A)
    preamble += assemble(ADD, C, A)
    # Top of the loop.
    ucode = assemble(SUB, B, 0x1)
    ucode += assemble(SUB, C, 0x1)
    ucode += assemble(IFE, [B], [C])
    ucode += assemble(BOR, X, 0xffff)
    ucode = until(ucode, (IFN, A, 0x0))
    ucode += assemble(SET, A, X)
    ucode += assemble(XOR, A, 0xffff)
    # Restore X.
    ucode += assemble(SET, X, POP)
    ucode += assemble(SET, PC, POP)
    return preamble + ucode


def memcpy():
    """
    Copy A bytes from B to C. Clobbers A.

    The copy is made back to front. No overlapping check is done.
    """

    preamble = assemble(ADD, B, A)
    preamble += assemble(ADD, C, A)
    # Top of the loop.
    ucode = assemble(SUB, A, 0x1)
    ucode += assemble(SUB, B, 0x1)
    ucode += assemble(SUB, C, 0x1)
    ucode += assemble(SET, [C], [B])
    ucode = until(ucode, (IFN, A, 0x0))
    # And return.
    ucode += assemble(SET, PC, POP)
    return preamble + ucode


def read(register):
    """
    Get a byte from the keyboard and put it in the given register.

    This blocks.
    """

    ucode = assemble(SET, register, [0x9010])
    ucode = until(ucode, (IFE, register, 0x0))
    ucode += assemble(SET, [0x9010], 0x0)
    ucode += assemble(SET, PC, POP)
    return ucode


def write(register):
    """
    Write a byte to the framebuffer.

    The register needs to not be PEEK or POP, because SP is modified when this
    function is entered.

    Self-modifying code is used to track the cursor in the framebuffer.
    """

    # Save Y.
    ucode = assemble(SET, PUSH, Y)
    # Save Z.
    ucode += assemble(SET, PUSH, Z)
    # Save the data that we're supposed to push.
    ucode = assemble(SET, PUSH, register)
    # Do some tricky PC manipulation to get a bareword into the code, and
    # sneak its address into Z.
    ucode += assemble(SET, Z, PC)
    ucode += assemble(IFE, 0x0, 0x0)
    ucode += "\x80\x00"
    ucode += assemble(ADD, Z, 0x1)
    # Dereference the framebuffer.
    ucode += assemble(SET, Y, [Z])
    # Write to the framebuffer.
    ucode += assemble(SET, [Y], POP)
    # Advance the framebuffer.
    ucode += assemble(ADD, [Z], 0x1)
    # If the framebuffer has wrapped, wrap the pointer.
    ucode += assemble(IFG, 0x8200, [Z])
    ucode += assemble(SUB, [Z], 0x200)
    # Restore registers and leave.
    ucode += assemble(SET, Z, POP)
    ucode += assemble(SET, Y, POP)
    ucode += assemble(SET, PC, POP)
    return ucode


library = {
    "memcmp": memcmp,
    "memcpy": memcpy,
}
