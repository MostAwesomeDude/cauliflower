from unittest import TestCase

from cauliflower.assembler import A, SET, assemble

class TestAssembler(TestCase):

    def test_set_register_literal(self):
        expected = "\x7c\x01\x00\x30"
        self.assertEqual(expected, assemble(SET, A, 0x30))
