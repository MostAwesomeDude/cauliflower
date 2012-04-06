"""
Flow control and ABI helpers.
"""

from cauliflower.assembler import A, ADD, PC, SET, SUB, Z, Absolute, assemble


def call(target):
    """
    Call a subroutine.

    This call is built to be position-independent. The return value pushed
    onto the stack is calculated at runtime, and the return/call stack is
    managed by this function, so no effort is required beyond ensuring that
    the target is already fixed in location.

    Safety not guaranteed; you might not ever come back.
    """

    # Make space on the call stack.
    ucode = assemble(SUB, Z, 0x1)
    # Hax. Calculate where we currently are based on PC, and then expect that
    # we will take a certain number of words to make our actual jump.
    # Grab PC into a GPR. Note that PC increments before it's grabbed here, so
    # this instruction doesn't count towards our total.
    ucode += assemble(SET, A, PC)
    # 0x0+1: Add our offset to PC in A.
    ucode += assemble(ADD, A, 0x4)
    # 0x1+1: Push our offset into the ret/call stack on Z.
    ucode += assemble(SET, [Z], A)
    # 0x2+2: Make our call, rigged so that it will always be two words.
    ucode += assemble(SET, PC, Absolute(target))
    # 0x4 is business as usual. Whereever we were from, we *probably* wanna
    # decrement Z again.
    ucode += assemble(ADD, Z, 0x1)
    return ucode


def ret():
    """
    Return to the caller.

    It's totally possible to return to lala-land with this function. Don't use
    it if you are not confident that the caller actually pushed a return
    location onto the return/call stack.
    """

    return assemble(SET, PC, [Z])
