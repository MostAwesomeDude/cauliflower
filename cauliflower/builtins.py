from cauliflower.assembler import (A, ADD, AND, B, BOR, C, DIV, MOD, MUL,
                                   PEEK, POP, PUSH, SET, SP, SUB, XOR,
                                   assemble)

def drop():
    return assemble(ADD, SP, 0x1)

def dup():
    ucode = assemble(SET, A, PEEK)
    ucode += assemble(SET, PUSH, A)
    return ucode

def over():
    ucode = assemble(SET, A, SP)
    ucode += assemble(SET, PUSH, [A + 0x1])
    return ucode

def rot():
    ucode = assemble(SET, A, POP)
    ucode += assemble(SET, B, POP)
    ucode += assemble(SET, C, POP)
    ucode += assemble(SET, PUSH, B)
    ucode += assemble(SET, PUSH, A)
    ucode += assemble(SET, PUSH, C)
    return ucode

def swap():
    ucode = assemble(SET, A, POP)
    ucode += assemble(SET, B, POP)
    ucode += assemble(SET, PUSH, A)
    ucode += assemble(SET, PUSH, B)
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
    "mod": MOD,
    "and": AND,
    "invert": XOR,
    "or": BOR,
}

def binop(op):
    """
    Compile a binary operation.
    """

    opcode = binops[op]

    ucode = assemble(SET, A, POP)
    ucode += assemble(opcode, PEEK, A)
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
