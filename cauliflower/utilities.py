from cauliflower.assembler import (A, ADD, B, BOR, C, IFE, IFN, PC, POP, PUSH,
                                   SET, SUB, X, XOR, assemble, until)

# All of these utility functions expect SP to point to their caller, or at
# least where their caller would like to return to, and assume that SP is safe
# to push onto.

def memcmp():
    """
    Put a length in A, two addresses in B and C, and fill A with whether
    they match (non-zero) or don't match (zero). Clobbers X.
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