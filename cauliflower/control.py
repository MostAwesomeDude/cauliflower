"""
Flow control and ABI helpers.
"""

from cauliflower.assembler import (A, ADD, IFE, PC, POP, SET, SUB, Z,
                                   Absolute, assemble)


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


def if_alone(target):
    """
    Consider the current value on the stack. If it's true, then execute a
    given code block. Otherwise, jump to the next code block.
    """

    print "Making if", hex(target)

    # We don't know the size of the block we wish to jump over quite yet;
    # let's figure that out first.
    block = call(target)

    # Our strategy is to put together a small jump over the block if the value
    # is false. If it's true, then the IFE will jump over the jump. Double
    # negatives fail to lose again!
    ucode = assemble(IFE, 0x0, POP)
    # Now we jump over the block...
    ucode += assemble(ADD, PC, len(block) // 2)
    # And insert the call to the block.
    ucode += block
    # All done!
    return ucode


def if_else(target, otherwise):
    """
    Add a call to a block directly after an if statement. The block will only
    be executed if the if block was not executed.
    """

    print "Making if/else", hex(target), hex(otherwise)

    # We don't know the size of the block we wish to jump over quite yet;
    # let's figure that out first.
    ifblock = call(target)

    # Let's also make the else block.
    elseblock = call(otherwise)

    # Same as before, but with a twist: At the end of the ifblock, we're going
    # to jump over the else block in the same style.
    ifblock += assemble(ADD, PC, len(elseblock) // 2)

    # Now assemble as before. First, the test.
    ucode = assemble(IFE, 0x0, POP)
    # Now we jump over the block...
    ucode += assemble(ADD, PC, len(ifblock) // 2)
    # And insert the call to the block.
    ucode += ifblock
    # Now the else block.
    ucode += elseblock
    # All done!
    return ucode
