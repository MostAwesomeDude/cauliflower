from unittest import TestCase

from cauliflower.assembler import A, PC, PUSH, SET, assemble

class TestAssembler(TestCase):

    def test_set_pc_literal(self):
        expected = "\xc5\xc1"
        self.assertEqual(expected, assemble(SET, PC, 0x11))

    def test_set_pc_literal_long(self):
        expected = "\x7d\xc1\x12\x34"
        self.assertEqual(expected, assemble(SET, PC, 0x1234))

    def test_set_push_literal(self):
        expected = "\x89\xa1"
        self.assertEqual(expected, assemble(SET, PUSH, 0x2))

    def test_set_register_literal(self):
        expected = "\x7c\x01\x00\x30"
        self.assertEqual(expected, assemble(SET, A, 0x30))
