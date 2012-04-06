===========
Cauliflower
===========

Cauliflower is a minimal Forth implementation which statically compiles to
Notch's CPU bytecote. It does not support much beyond arithmetic, which is
fine because neither does Notch's CPU.

At the moment, Cauliflower emits a completely static binary executable which
runs on the raw CPU. There is no reflection or dynamic compilation.

Words
=====

There are some primitive words which are emitted directly as assembly:

 * drop
 * dup
 * over
 * rot
 * swap
 * \+, \-, \*, /
 * and, invert, or
 * >r, r@, rdrop

There are composite words in an included prelude, too.

 * 2dup
 * r>

Missing Words
=============

Some words are not implemented because they are difficult to implement.
Intrepid programmers could probably hack these up quickly. Alternatively, I'm
probably gonna get these in there at some point.

 * constant
 * pick, roll
 * if, else, then
 * test, loop
 * begin, while, repeat

Some are not implemented because they require I/O. Seriously, without I/O it
doesn't make sense to be able to print to the terminal.

 * .
 * cr

Some are not implemented because we aren't sure about the behavior of the CPU.
Hash tables are a little tricky to get right under even the best of
circumstances.

 * !
 * ?
 * @

And some are not implemented because the implementation can't adjust or
examine the dictionary at runtime. These could be implemented, someday, if
needed.

 * \\
 * see
 * words
