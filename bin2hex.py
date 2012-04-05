#!/usr/bin/env python

from itertools import izip
import sys

it = iter(sys.stdin.read())
for first, second in izip(it, it):
    print "%02X%02X" % (ord(first), ord(second))
