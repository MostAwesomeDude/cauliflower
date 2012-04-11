from unittest import TestCase

from cauliflower.assembler import A, JSR, PC, PUSH, SET, Z, Absolute, assemble

class TestAssembler(TestCase):

    def test_jsr_literal(self):
        expected = "\x7c\x10\x00\x42"
        self.assertEqual(expected, assemble(JSR, 0x42))

    def test_set_pc_literal(self):
        expected = "\xc5\xc1"
        self.assertEqual(expected, assemble(SET, PC, 0x11))

    def test_set_pc_literal_absolute(self):
        expected = "\x7d\xc1\x00\x11"
        self.assertEqual(expected, assemble(SET, PC, Absolute(0x11)))

    def test_set_pc_literal_long(self):
        expected = "\x7d\xc1\x12\x34"
        self.assertEqual(expected, assemble(SET, PC, 0x1234))

    def test_set_pc_z_offset(self):
        expected = "\x55\xc1\x12\x34"
        self.assertEqual(expected, assemble(SET, PC, [Z + 0x1234]))

    def test_set_push_literal(self):
        expected = "\x89\xa1"
        self.assertEqual(expected, assemble(SET, PUSH, 0x2))

    def test_set_push_z(self):
        expected = "\x15\xa1"
        self.assertEqual(expected, assemble(SET, PUSH, Z))

    def test_set_register_literal(self):
        expected = "\x7c\x01\x00\x30"
        self.assertEqual(expected, assemble(SET, A, 0x30))
