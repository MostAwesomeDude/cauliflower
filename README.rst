===========
Cauliflower
===========

Cauliflower is a minimal Forth implementation which statically compiles to
Notch's CPU bytecote. It does not support much beyond arithmetic, which is
fine because neither does Notch's CPU.

Words
=====

The primitive words:

 * drop
 * dup
 * over
 * rot
 * swap

The arithmetic operators:

 * +
 * -
 * *
 * /
 * and
 * invert
 * or

Missing Words
=============

Some words are not implemented because they are difficult to implement:

 * constant
 * pick, roll
 * if, else, then
 * test, loop
 * begin, while, repeat

Some are not implemented because they require I/O:

 * .
 * cr

Some are not implemented because we aren't sure about the behavior of the CPU:

 * !
 * ?
 * @
