#!/usr/bin/env python3
"""Regression tests for the C128 BASIC 7.0 toolchain."""

from __future__ import annotations

import unittest

from bas2prg import Bas2Prg, TOKEN_BY_TEXT, iter_tokenized_program
from c128_syntax_checker import check_source


class Bas2PrgTests(unittest.TestCase):
    def test_manual_program_storage_layout(self) -> None:
        # Matches the memory example in C-128 BASIC 7.0 Internals:
        # 10 PRINT"HELLO"
        # 20 END
        actual = Bas2Prg(invert_case=True).convert('10 print"hello"\n20 end\n')
        expected = bytes.fromhex(
            "01 1c "
            "0e 1c 0a 00 99 22 48 45 4c 4c 4f 22 00 "
            "14 1c 14 00 80 00 "
            "00 00"
        )
        self.assertEqual(actual, expected)

    def test_extended_function_tokens(self) -> None:
        expected = {
            "POT":"ce02", "BUMP":"ce03", "PEN":"ce04",
            "RSPPOS":"ce05", "RSPRITE":"ce06", "RSPCOLOR":"ce07",
            "XOR":"ce08", "RWINDOW":"ce09", "POINTER":"ce0a",
        }
        for name, value in expected.items():
            self.assertEqual(TOKEN_BY_TEXT[name].hex(), value)

    def test_extended_statement_tokens(self) -> None:
        expected = {
            "BANK":"fe02", "FILTER":"fe03", "PLAY":"fe04", "TEMPO":"fe05",
            "MOVSPR":"fe06", "SPRITE":"fe07", "SPRCOLOR":"fe08", "RREG":"fe09",
            "ENVELOPE":"fe0a", "SLEEP":"fe0b", "CATALOG":"fe0c", "DOPEN":"fe0d",
            "APPEND":"fe0e", "DCLOSE":"fe0f", "BSAVE":"fe10", "BLOAD":"fe11",
            "RECORD":"fe12", "CONCAT":"fe13", "DVERIFY":"fe14", "DCLEAR":"fe15",
            "SPRSAV":"fe16", "COLLISION":"fe17", "BEGIN":"fe18", "BEND":"fe19",
            "WINDOW":"fe1a", "BOOT":"fe1b", "WIDTH":"fe1c", "SPRDEF":"fe1d",
            "QUIT":"fe1e", "STASH":"fe1f", "FETCH":"fe21", "SWAP":"fe23",
            "OFF":"fe24", "FAST":"fe25", "SLOW":"fe26",
        }
        for name, value in expected.items():
            self.assertEqual(TOKEN_BY_TEXT[name].hex(), value)

    def test_composite_source_forms(self) -> None:
        prg = Bas2Prg(invert_case=True).convert(
            "10 getkey a$\n"
            "20 go64\n"
            "30 print using \"###\";a\n"
        )
        lines = dict(iter_tokenized_program(prg))
        self.assertTrue(lines[10].startswith(bytes.fromhex("a1 f9")))
        self.assertTrue(lines[20].startswith(bytes.fromhex("cb 36 34")))
        self.assertIn(bytes.fromhex("99"), lines[30])
        self.assertIn(bytes.fromhex("fb"), lines[30])

    def test_strings_rem_and_data_are_not_keyword_tokenized(self) -> None:
        prg = Bas2Prg(invert_case=True).convert(
            '10 print"play sprite bank"\n'
            '20 rem play sprite bank\n'
            '30 data play,sprite,bank:read a$,b$,c$\n'
        )
        lines = dict(iter_tokenized_program(prg))
        self.assertNotIn(bytes.fromhex("fe04"), lines[10])  # PLAY
        self.assertNotIn(bytes.fromhex("fe07"), lines[10])  # SPRITE
        self.assertNotIn(bytes.fromhex("fe02"), lines[10])  # BANK
        self.assertNotIn(bytes.fromhex("fe04"), lines[20])
        self.assertNotIn(bytes.fromhex("fe04"), lines[30])
        self.assertIn(bytes.fromhex("87"), lines[30])       # READ after ':'


class SyntaxCheckerTests(unittest.TestCase):
    def test_valid_basic7_program(self) -> None:
        source = """\
10 graphic 0
20 scnclr 0
30 sprite 1,1,3
40 movspr 1,100,100
50 do
60 j=joy(2)
70 if (j and 128)=128 then exit
80 loop
90 sprite 1,0
100 end
"""
        errors = [i for i in check_source(source, reachability=False) if i.severity == "ERROR"]
        self.assertEqual(errors, [])

    def test_ai_style_errors_are_detected(self) -> None:
        source = """\
10 cls
20 score=1
30 bank 17
40 sprite 9,1,3
50 if a=1 print "missing then"
60 do
70 print "open loop"
80 goto 999
"""
        issues = check_source(source, reachability=False)
        codes = {i.code for i in issues if i.severity == "ERROR"}
        self.assertTrue({
            "UNKNOWN_STATEMENT", "KEYWORD_IN_VARIABLE", "RANGE",
            "IF_THEN", "DO_WITHOUT_LOOP", "MISSING_TARGET"
        }.issubset(codes))


if __name__ == "__main__":
    unittest.main(verbosity=2)
