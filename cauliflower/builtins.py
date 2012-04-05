from cauliflower.assembler import (ADD, AND, BOR, DIV, J, MUL, PEEK, POP,
                                   PUSH, SET, SP, SUB, XOR, assemble)

def drop():
    return assemble(ADD, SP, 0x1)

def dup():
    ucode = assemble(SET, J, PEEK)
    ucode += assemble(SET, PUSH, J)
    return ucode

def over():
    # XXX this could be far better if our assembler could cobble together
    # things like [SP + 1]
    # ucode = assemble(SET, J, [SP + 0x1])
    ucode = assemble(SET, J, SP)
    ucode += assemble(ADD, J, 0x1)
    ucode += assemble(SET, PUSH, [J])
    return ucode

def rot():
    # XXX ugh, is this really the best way?
    ucode = assemble(SET, J, POP)
    ucode += assemble(SET, I, POP)
    ucode += assemble(SET, Z, POP)
    ucode += assemble(SET, PUSH, I)
    ucode += assemble(SET, PUSH, J)
    ucode += assemble(SET, PUSH, Z)
    return ucode

def swap():
    ucode = assemble(SET, J, POP)
    ucode += assemble(SET, I, POP)
    ucode += assemble(SET, PUSH, J)
    ucode += assemble(SET, PUSH, I)
    return ucode

prims = {
    "drop": drop,
    "dup": dup,
    "over": over,
    "rot": rot,
    "swap": swap,
}

binops = {
    "*": MUL,
    "+": ADD,
    "-": SUB,
    "/": DIV,
    "and": AND,
    "invert": XOR,
    "or": BOR,
}

def binop(op):
    """
    Compile a binary operation.
    """

    opcode = binops[op]

    ucode = assemble(SET, J, POP)
    ucode += assemble(opcode, PEEK, J)
    return ucode


def builtin(word):
    """
    Compile a builtin word.
    """

    try:
        i = int(word)
        ucode = assemble(SET, PUSH, i)
        return ucode
    except ValueError:
        pass

    if word in prims:
        return prims[word]()

    if word in binops:
        return binop(word)

    raise Exception("Don't know builtin %r" % word)
