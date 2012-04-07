===========
Cauliflower
===========

Cauliflower is a minimal Forth implementation which statically compiles to
Notch's CPU bytecode. It does not support much beyond arithmetic, which is
fine because neither does Notch's CPU. In particular, Cauliflower does not
support any of the theoretical video or keyboard extensions which some
emulators have grafted on.

However, Cauliflower does some small per-word optimizations which give it an
edge over writing raw assembly. It can inline small words and words marked
with the ``inline`` word in order to improve performance. And, of course,
writing Forth is a lot more fun than writing assembly.

At the moment, Cauliflower emits a completely static binary executable which
runs on the raw CPU. There is no reflection or dynamic compilation.

Like many Forths, Cauliflower does not support mutual recursion; words must be
fully defined before they can be used.

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

And then there are words which control compilation.

 * : and ;
 * ( and )
 * inline
 * if, else, then

There are composite words in an included prelude, too.

 * 2dup, 2drop
 * nip, tuck
 * r>

Missing Words
=============

Some words are not implemented because they are difficult to implement.
Intrepid programmers could probably hack these up quickly. Alternatively, I'm
probably gonna get these in there at some point.

 * constant
 * pick, roll
 * test, loop
 * begin, while, repeat
 * depth

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

Limitations
===========

``if``/``else``/``then`` statements cannot be nested due to a weakness with
the tokenizer. This limitation could be worked around if needed, although as a
matter of code style it is highly recommended to just make more words.
