#!/usr/bin/env python3
"""
c128_syntax_checker.py — static checker for Commodore 128 BASIC 7.0 source.

This checker is deliberately aimed at code that will be tokenized and executed on a
real C128 / VICE in native C128 mode. It catches common AI-generated mistakes before
bas2prg.py is run.

It is not a full emulation of the BASIC 7.0 interpreter. 0 ERRORs means that the
source passed the checks implemented here; runtime logic still needs testing in VICE
or on real hardware.

Usage:
    python c128_syntax_checker.py program.bas
    python c128_syntax_checker.py program.bas --json
    python c128_syntax_checker.py program.bas --no-reach
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

MAX_LINE_NUMBER = 63999
MAX_SOURCE_LINE_CHARS = 160

# BASIC 7.0 keyword set. Composite source forms such as GETKEY are represented
# separately because the ROM stores GET + KEY as two tokens.
KEYWORDS = {
    "END","FOR","NEXT","DATA","INPUT#","INPUT","DIM","READ","LET","GOTO","RUN",
    "IF","RESTORE","GOSUB","GO TO","RETURN","REM","STOP","ON","WAIT","LOAD","SAVE",
    "VERIFY","DEF","POKE","PRINT#","PRINT","CONT","LIST","CLR","CMD","SYS","OPEN",
    "CLOSE","GET","NEW","TAB(","TO","FN","SPC(","THEN","NOT","STEP","AND","OR",
    "SGN","INT","ABS","USR","FRE","POS","SQR","RND","LOG","EXP","COS","SIN",
    "TAN","ATN","PEEK","LEN","STR$","VAL","ASC","CHR$","LEFT$","RIGHT$","MID$",
    "GO","RGR","RCLR","JOY","RDOT","DEC","HEX$","ERR$","INSTR","ELSE","RESUME",
    "TRAP","TRON","TROFF","SOUND","VOL","AUTO","PUDEF","GRAPHIC","PAINT","CHAR",
    "BOX","CIRCLE","GSHAPE","SSHAPE","DRAW","LOCATE","COLOR","SCNCLR","SCALE",
    "HELP","DO","LOOP","EXIT","DIRECTORY","DSAVE","DLOAD","HEADER","SCRATCH",
    "COLLECT","COPY","RENAME","BACKUP","DELETE","RENUMBER","KEY","MONITOR","USING",
    "UNTIL","WHILE","POT","BUMP","PEN","RSPPOS","RSPRITE","RSPCOLOR","XOR",
    "RWINDOW","POINTER","BANK","FILTER","PLAY","TEMPO","MOVSPR","SPRITE",
    "SPRCOLOR","RREG","ENVELOPE","SLEEP","CATALOG","DOPEN","APPEND","DCLOSE",
    "BSAVE","BLOAD","RECORD","CONCAT","DVERIFY","DCLEAR","SPRSAV","COLLISION",
    "BEGIN","BEND","WINDOW","BOOT","WIDTH","SPRDEF","QUIT","STASH","FETCH","SWAP",
    "OFF","FAST","SLOW",
}
COMPOSITE_FORMS = {"GETKEY", "GO64"}
UNIMPLEMENTED = {"OFF", "QUIT"}

RESERVED_SYSTEM_NAMES = {"DS", "DS$", "EL", "ER", "ERR$", "ST", "TI", "TI$"}

# These are editing/interactive facilities for which use inside stored programs is
# suspicious. They are warnings, not errors, because exact direct-mode restrictions
# differ by command/context.
INTERACTIVE_COMMANDS = {"AUTO", "DELETE", "RENUMBER", "MONITOR", "SPRDEF", "NEW", "LIST"}

# Functions for useful argument-count validation. Unknown/complex forms are intentionally
# omitted rather than guessed.
FUNCTION_ARITY: dict[str, tuple[int, int]] = {
    "ABS": (1,1), "ASC": (1,1), "ATN": (1,1), "CHR$": (1,1),
    "COS": (1,1), "DEC": (1,1), "ERR$": (1,1), "EXP": (1,1),
    "FRE": (1,1), "HEX$": (1,1), "INSTR": (2,3), "INT": (1,1),
    "JOY": (1,1), "LEFT$": (2,2), "LEN": (1,1), "LOG": (1,1),
    "MID$": (2,3), "PEEK": (1,1), "PEN": (1,1), "POINTER": (1,1),
    "POS": (1,1), "POT": (1,1), "BUMP": (1,1), "RDOT": (1,1),
    "RIGHT$": (2,2), "RND": (0,1), "RSPPOS": (2,2), "RSPRITE": (2,2),
    "RWINDOW": (1,1), "SGN": (1,1), "SIN": (1,1), "SQR": (1,1),
    "STR$": (1,1), "TAN": (1,1), "VAL": (1,1),
}

LINE_RE = re.compile(r"^\s*(\d{1,5})(?:\s*)(.*)$")
VAR_RE = re.compile(r"^[A-Za-z][A-Za-z0-9]*(?:[$%])?$")
NUMBER_RE = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][+-]?\d+)?$")


@dataclass
class BasicLine:
    number: int
    physical_line: int
    raw: str
    content: str


@dataclass
class Issue:
    line: int | None
    severity: str
    code: str
    message: str


def _split_statements(text: str) -> list[str]:
    """Split at ':' outside strings. REM consumes the remainder."""
    parts: list[str] = []
    buf: list[str] = []
    in_string = False
    i = 0
    upper = text.upper()

    while i < len(text):
        ch = text[i]
        if ch == '"':
            in_string = not in_string
            buf.append(ch)
            i += 1
            continue

        if not in_string and upper.startswith("REM", i):
            # Treat REM as a command when it starts a statement or follows a separator/
            # whitespace. This is enough for static analysis while avoiding words in strings.
            before = text[i-1] if i else ":"
            if i == 0 or before.isspace() or before == ":":
                buf.append(text[i:])
                i = len(text)
                break

        if not in_string and ch == ":":
            parts.append("".join(buf))
            buf = []
            i += 1
            continue

        buf.append(ch)
        i += 1

    parts.append("".join(buf))
    return parts


def _mask_strings(text: str) -> str:
    out: list[str] = []
    in_string = False
    for ch in text:
        if ch == '"':
            in_string = not in_string
            out.append(" ")
        elif in_string:
            out.append(" ")
        else:
            out.append(ch)
    return "".join(out)


def _strip_rem(text: str) -> str:
    in_string = False
    upper = text.upper()
    i = 0
    while i < len(text):
        if text[i] == '"':
            in_string = not in_string
            i += 1
            continue
        if not in_string and upper.startswith("REM", i):
            before = text[i-1] if i else ":"
            if i == 0 or before.isspace() or before == ":":
                return text[:i]
        i += 1
    return text


def _identifier_type(name: str) -> str:
    return "string" if name.endswith("$") else "integer" if name.endswith("%") else "float"


def _significant_name(name: str) -> str:
    base = name.rstrip("$%").upper()
    return base[:2] + ("$" if name.endswith("$") else "%" if name.endswith("%") else "")


def _keyword_inside(name: str) -> str | None:
    base = name.rstrip("$%").upper()
    # Only alphabetic keyword fragments matter for variable names.
    candidates = sorted(
        {k.rstrip("(") for k in KEYWORDS if k.rstrip("(").isalpha() and len(k.rstrip("(")) >= 2},
        key=len,
        reverse=True,
    )
    for kw in candidates:
        if kw in base:
            return kw
    return None


def _count_args(arg_text: str) -> int:
    if not arg_text.strip():
        return 0
    count = 1
    depth = 0
    in_string = False
    for ch in arg_text:
        if ch == '"':
            in_string = not in_string
        elif not in_string:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth = max(0, depth - 1)
            elif ch == "," and depth == 0:
                count += 1
    return count


def _extract_call(text: str, open_pos: int) -> tuple[str, int] | None:
    depth = 0
    in_string = False
    start = open_pos + 1
    for i in range(open_pos, len(text)):
        ch = text[i]
        if ch == '"':
            in_string = not in_string
        if in_string:
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return text[start:i], i
    return None


class SyntaxChecker:
    def __init__(self, reachability: bool = True) -> None:
        self.lines: list[BasicLine] = []
        self.line_map: dict[int, BasicLine] = {}
        self.issues: list[Issue] = []
        self.reachability = reachability
        self.variable_spellings: dict[str, set[str]] = {}

    def add(self, line: int | None, severity: str, code: str, message: str) -> None:
        self.issues.append(Issue(line, severity, code, message))

    def load(self, source: str) -> None:
        self.lines.clear()
        self.line_map.clear()

        for physical, raw in enumerate(source.splitlines(), start=1):
            if not raw.strip():
                continue
            m = LINE_RE.match(raw)
            if not m:
                self.add(None, "ERROR", "LINE_NUMBER", f"physical line {physical}: missing/invalid BASIC line number")
                continue

            number = int(m.group(1))
            content = m.group(2)

            if number > MAX_LINE_NUMBER:
                self.add(number, "ERROR", "LINE_RANGE", f"line number must be 0..{MAX_LINE_NUMBER}")
            if number in self.line_map:
                self.add(number, "ERROR", "DUPLICATE_LINE", "duplicate BASIC line number")

            # Count the actual .bas source line without CR/LF.
            if len(raw) > MAX_SOURCE_LINE_CHARS:
                self.add(
                    number, "ERROR", "LINE_LENGTH",
                    f"{len(raw)} characters; C128 BASIC program lines are limited to {MAX_SOURCE_LINE_CHARS}"
                )

            bl = BasicLine(number, physical, raw, content)
            self.lines.append(bl)
            self.line_map[number] = bl

    def validate(self) -> list[Issue]:
        self._check_order()
        self._check_quotes_parentheses()
        self._check_unimplemented_and_unknown_statements()
        self._check_variables()
        self._check_if_else_begin_bend()
        self._check_loops()
        self._check_targets()
        self._check_functions()
        self._check_static_ranges()
        self._check_interactive_commands()
        if self.reachability:
            self._check_reachability()
        return self.issues

    def _check_order(self) -> None:
        previous = -1
        for bl in self.lines:
            if bl.number <= previous:
                self.add(
                    bl.number, "ERROR", "LINE_ORDER",
                    f"line numbers must be strictly ascending; previous line is {previous}"
                )
            previous = bl.number

    def _check_quotes_parentheses(self) -> None:
        for bl in self.lines:
            if bl.content.count('"') % 2:
                self.add(bl.number, "ERROR", "QUOTE", "unmatched double quote")

            text = _strip_rem(bl.content)
            in_string = False
            depth = 0
            for ch in text:
                if ch == '"':
                    in_string = not in_string
                    continue
                if in_string:
                    continue
                if ch == "(":
                    depth += 1
                elif ch == ")":
                    depth -= 1
                    if depth < 0:
                        self.add(bl.number, "ERROR", "PAREN", "closing parenthesis without opening parenthesis")
                        break
            if depth > 0:
                self.add(bl.number, "ERROR", "PAREN", f"{depth} unclosed parenthesis/parentheses")

    def _statement_head(self, statement: str) -> str:
        s = statement.strip()
        if not s:
            return ""
        if s.startswith("?"):
            return "?"
        m = re.match(r"([A-Za-z]+#?)", s)
        return m.group(1).upper() if m else ""

    def _known_statement_prefix(self, statement: str) -> bool:
        s = statement.lstrip()
        u = s.upper()
        if not s:
            return True
        if s.startswith("?"):
            return False  # shorthand deliberately rejected for .bas source

        # Assignment, including optional LET.
        if re.match(r"(?:LET\s*)?[A-Za-z][A-Za-z0-9]*[$%]?\s*(?:\([^)]*\))?\s*=", s, re.I):
            return True

        # BASIC permits compact forms (e.g. FORI=1TO10), so use startswith.
        statement_keywords = sorted(
            {
                "END","FOR","NEXT","DATA","INPUT#","INPUT","DIM","READ","LET","GOTO","GO TO","RUN",
                "IF","RESTORE","GOSUB","RETURN","REM","STOP","ON","WAIT","LOAD","SAVE",
                "VERIFY","DEF","POKE","PRINT#","PRINT","CONT","LIST","CLR","CMD","SYS",
                "OPEN","CLOSE","GET","NEW","TRAP","TRON","TROFF","SOUND","VOL","AUTO",
                "PUDEF","GRAPHIC","PAINT","CHAR","BOX","CIRCLE","GSHAPE","SSHAPE","DRAW",
                "LOCATE","COLOR","SCNCLR","SCALE","HELP","DO","LOOP","EXIT","DIRECTORY",
                "DSAVE","DLOAD","HEADER","SCRATCH","COLLECT","COPY","RENAME","BACKUP",
                "DELETE","RENUMBER","KEY","MONITOR","RESUME","BANK","FILTER","PLAY",
                "TEMPO","MOVSPR","SPRITE","SPRCOLOR","RREG","ENVELOPE","SLEEP","CATALOG",
                "DOPEN","APPEND","DCLOSE","BSAVE","BLOAD","RECORD","CONCAT","DVERIFY",
                "DCLEAR","SPRSAV","COLLISION","BEGIN","BEND","WINDOW","BOOT","WIDTH",
                "SPRDEF","QUIT","STASH","FETCH","SWAP","OFF","FAST","SLOW","GETKEY","GO64"
            },
            key=len,
            reverse=True,
        )
        return any(u.startswith(kw) for kw in statement_keywords)

    def _check_unimplemented_and_unknown_statements(self) -> None:
        for bl in self.lines:
            for statement in _split_statements(bl.content):
                s = statement.strip()
                if not s:
                    continue
                u = _mask_strings(s).upper()

                if s.startswith("?"):
                    self.add(
                        bl.number, "ERROR", "ABBREVIATION",
                        "use PRINT in source, not '?' editor abbreviation"
                    )
                    continue

                if re.match(r"^REM(?:\s|$)", u):
                    break
                if re.match(r"^DATA(?:\s|$)", u):
                    continue

                for bad in UNIMPLEMENTED:
                    if re.search(rf"(?<![A-Z0-9]){bad}(?![A-Z0-9])", u):
                        self.add(
                            bl.number, "ERROR", "UNIMPLEMENTED",
                            f"{bad} has a BASIC 7.0 token but is unimplemented on the C128"
                        )

                # ELSE and the THEN clause can make the statement head look unusual.
                if re.match(r"^(ELSE|THEN|BEND)\b", u):
                    continue
                if not self._known_statement_prefix(s):
                    head = self._statement_head(s) or s.split()[0]
                    self.add(
                        bl.number, "ERROR", "UNKNOWN_STATEMENT",
                        f"unsupported or unrecognized statement start '{head}'"
                    )

    def _record_variable(self, line: int, name: str, context: str) -> None:
        n = name.upper()
        if not VAR_RE.match(n):
            return
        base = n.rstrip("$%")
        # A regex that searches assignments can encounter a keyword immediately
        # before a parenthesized expression (e.g. IF (J AND 128)=128). Keywords
        # are language tokens, never candidate variable names.
        if n in KEYWORDS or n in COMPOSITE_FORMS:
            return
        if n in RESERVED_SYSTEM_NAMES:
            # Reading system variables is valid; assigning them as ordinary program
            # variables is almost always an error. Context decides severity.
            if context in {"assignment", "for", "input", "read", "get", "dim", "next"}:
                self.add(line, "ERROR", "RESERVED_VARIABLE", f"{n} is a reserved C128 system name")
            return

        if len(base) > 2:
            self.add(
                line, "WARN", "VARIABLE_LENGTH",
                f"variable '{n}' uses more than two characters; BASIC 7.0 distinguishes only the first two"
            )

        kw = _keyword_inside(n)
        if kw:
            self.add(
                line, "ERROR", "KEYWORD_IN_VARIABLE",
                f"variable '{n}' contains BASIC keyword '{kw}' and will tokenize incorrectly"
            )

        sig = _significant_name(n)
        self.variable_spellings.setdefault(sig, set()).add(n)

    def _check_variables(self) -> None:
        assignment = re.compile(r"(?<![A-Za-z0-9])([A-Za-z][A-Za-z0-9]*[$%]?)\s*(?:\([^=\n]*\))?\s*=", re.I)
        for_re = re.compile(r"\bFOR\s*([A-Za-z][A-Za-z0-9]*[%]?)\s*=", re.I)
        next_re = re.compile(r"\bNEXT\s*([A-Za-z][A-Za-z0-9]*[%]?)?", re.I)
        dim_re = re.compile(r"\bDIM\s+(.+)$", re.I)

        for bl in self.lines:
            text = _strip_rem(bl.content)
            masked = _mask_strings(text)

            for m in assignment.finditer(masked):
                self._record_variable(bl.number, m.group(1), "assignment")
            for m in for_re.finditer(masked):
                self._record_variable(bl.number, m.group(1), "for")
            for m in next_re.finditer(masked):
                if m.group(1):
                    self._record_variable(bl.number, m.group(1), "next")

            dm = dim_re.search(masked)
            if dm:
                for v in re.findall(r"([A-Za-z][A-Za-z0-9]*[$%]?)\s*\(", dm.group(1)):
                    self._record_variable(bl.number, v, "dim")

            for command, context in (("INPUT","input"),("READ","read"),("GETKEY","get"),("GET","get")):
                for m in re.finditer(rf"\b{command}\s+([^:]+)", masked, re.I):
                    tail = m.group(1)
                    for v in re.findall(r"(?<![A-Za-z0-9])([A-Za-z][A-Za-z0-9]*[$%]?)(?![A-Za-z0-9])", tail):
                        if v.upper() not in KEYWORDS:
                            self._record_variable(bl.number, v, context)

        for sig, names in sorted(self.variable_spellings.items()):
            if len(names) > 1:
                pretty = ", ".join(sorted(names))
                # Different long spellings collapse to one BASIC identifier.
                self.add(
                    None, "ERROR", "VARIABLE_COLLISION",
                    f"variables {pretty} collide as significant name '{sig}'"
                )

    def _check_if_else_begin_bend(self) -> None:
        begin_stack: list[int] = []

        for bl in self.lines:
            text = _mask_strings(_strip_rem(bl.content))
            u = text.upper()

            if re.search(r"(?<![A-Z])IF(?![A-Z])", u) and not re.search(r"(?<![A-Z])THEN(?![A-Z])", u):
                self.add(bl.number, "ERROR", "IF_THEN", "IF without THEN")

            if re.search(r"(?<![A-Z])ELSE(?![A-Z])", u):
                if not re.search(r":\s*ELSE(?![A-Z])", u):
                    self.add(
                        bl.number, "ERROR", "ELSE_COLON",
                        "ELSE must be separated from the preceding THEN/BEND clause by ':'"
                    )
                if not (
                    re.search(r"(?<![A-Z])IF(?![A-Z]).*(?<![A-Z])THEN(?![A-Z])", u)
                    or re.search(r"(?<![A-Z])BEND(?![A-Z])\s*:\s*ELSE", u)
                ):
                    self.add(
                        bl.number, "ERROR", "ELSE_CONTEXT",
                        "ELSE must belong to an IF...THEN on this line or to BEND:ELSE"
                    )

            # Process BEGIN/BEND in lexical order.
            for token in re.finditer(r"(?<![A-Z])(BEGIN|BEND)(?![A-Z])", u):
                word = token.group(1)
                if word == "BEGIN":
                    prefix = u[:token.start()]
                    if not (
                        re.search(r"(?<![A-Z])THEN(?![A-Z]).*$", prefix)
                        or re.search(r"(?<![A-Z])ELSE(?![A-Z]).*$", prefix)
                    ):
                        self.add(bl.number, "ERROR", "BEGIN_CONTEXT", "BEGIN must follow THEN or ELSE")
                    begin_stack.append(bl.number)
                else:
                    if not begin_stack:
                        self.add(bl.number, "ERROR", "BEND_WITHOUT_BEGIN", "BEND without matching BEGIN")
                    else:
                        begin_stack.pop()

        for start in begin_stack:
            self.add(start, "ERROR", "BEGIN_WITHOUT_BEND", "BEGIN has no matching BEND")

    def _check_loops(self) -> None:
        for_stack: list[tuple[int, str | None]] = []
        do_stack: list[int] = []

        for bl in self.lines:
            text = _mask_strings(_strip_rem(bl.content))
            # DATA payload is not executable source.
            statements = _split_statements(text)

            for statement in statements:
                s = statement.strip()
                if not s:
                    continue
                u = s.upper()
                if re.match(r"^DATA(?:\s|$)", u):
                    continue
                if re.match(r"^REM(?:\s|$)", u):
                    break

                # There may be multiple loop tokens in a compact statement.
                for m in re.finditer(r"(?<![A-Z])(FOR|NEXT|DO|LOOP|EXIT)(?![A-Z])", u):
                    word = m.group(1)
                    tail = u[m.end():]
                    if word == "FOR":
                        vm = re.match(r"\s*([A-Z][A-Z0-9]*%?)\s*=", tail)
                        for_stack.append((bl.number, vm.group(1) if vm else None))
                    elif word == "NEXT":
                        # RESUME NEXT is error-handling syntax, not a FOR/NEXT token pair.
                        prefix = u[:m.start()]
                        if re.search(r"\bRESUME\s*$", prefix):
                            continue
                        vm = re.match(
                            r"\s*([A-Z][A-Z0-9]*%?(?:\s*,\s*[A-Z][A-Z0-9]*%?)*)?",
                            tail
                        )
                        raw_vars = vm.group(1) if vm else None
                        next_vars = (
                            [v.strip() for v in raw_vars.split(",")]
                            if raw_vars else [None]
                        )
                        for nv in next_vars:
                            if not for_stack:
                                self.add(bl.number, "ERROR", "NEXT_WITHOUT_FOR", "NEXT without matching FOR")
                                break
                            start, fv = for_stack.pop()
                            if nv and fv and nv != fv:
                                self.add(
                                    bl.number, "ERROR", "NEXT_VARIABLE",
                                    f"NEXT {nv} does not match FOR {fv} at line {start}"
                                )
                    elif word == "DO":
                        do_stack.append(bl.number)
                    elif word == "LOOP":
                        if not do_stack:
                            self.add(bl.number, "ERROR", "LOOP_WITHOUT_DO", "LOOP without matching DO")
                        else:
                            do_stack.pop()
                    elif word == "EXIT":
                        if not do_stack:
                            self.add(bl.number, "ERROR", "EXIT_OUTSIDE_DO", "EXIT is only valid inside DO/LOOP")

        for start, var in for_stack:
            self.add(start, "ERROR", "FOR_WITHOUT_NEXT", f"FOR {var or '?'} has no matching NEXT")
        for start in do_stack:
            self.add(start, "ERROR", "DO_WITHOUT_LOOP", "DO has no matching LOOP")

    def _target_exists(self, source_line: int, target: int, kind: str) -> None:
        if target not in self.line_map:
            self.add(source_line, "ERROR", "MISSING_TARGET", f"{kind} target line {target} does not exist")

    def _check_targets(self) -> None:
        for bl in self.lines:
            text = _mask_strings(_strip_rem(bl.content))
            u = text.upper()

            # GOTO/GOSUB and GO TO.
            for m in re.finditer(r"(?<![A-Z])(?:GOTO|GO\s+TO|GOSUB)\s*(\d+)", u):
                self._target_exists(bl.number, int(m.group(1)), m.group(0).split()[0])

            # IF ... THEN line and ELSE line.
            for m in re.finditer(r"(?<![A-Z])(?:THEN|ELSE)\s*(\d+)", u):
                self._target_exists(bl.number, int(m.group(1)), m.group(0).split()[0])

            # TRAP/RESUME/RESTORE optional line target.
            for m in re.finditer(r"(?<![A-Z])(TRAP|RESUME|RESTORE)\s+(\d+)", u):
                self._target_exists(bl.number, int(m.group(2)), m.group(1))

            # COLLISION type,line calls a subroutine.
            for m in re.finditer(r"(?<![A-Z])COLLISION\s+[123]\s*,\s*(\d+)", u):
                self._target_exists(bl.number, int(m.group(1)), "COLLISION")

            # ON expr GOTO/GOSUB list.
            m = re.search(r"(?<![A-Z])ON\b(.+?)(GOTO|GOSUB)\s+([^:]+)", u)
            if m:
                targets = [x.strip() for x in m.group(3).split(",")]
                if not targets:
                    self.add(bl.number, "ERROR", "ON_TARGETS", f"ON {m.group(2)} has no targets")
                for target in targets:
                    if target.isdigit():
                        self._target_exists(bl.number, int(target), f"ON {m.group(2)}")
                    else:
                        self.add(bl.number, "ERROR", "ON_TARGETS", f"invalid ON {m.group(2)} target '{target}'")

    def _check_functions(self) -> None:
        for bl in self.lines:
            text = _strip_rem(bl.content)
            masked = _mask_strings(text)
            upper = masked.upper()

            for fn, (minimum, maximum) in FUNCTION_ARITY.items():
                pattern = re.compile(rf"(?<![A-Z0-9]){re.escape(fn)}\s*\(", re.I)
                for m in pattern.finditer(upper):
                    open_pos = upper.find("(", m.start())
                    call = _extract_call(text, open_pos)
                    if call is None:
                        continue
                    args, _ = call
                    count = _count_args(args)
                    if not minimum <= count <= maximum:
                        expected = str(minimum) if minimum == maximum else f"{minimum}..{maximum}"
                        self.add(
                            bl.number, "ERROR", "FUNCTION_ARITY",
                            f"{fn}() has {count} argument(s); expected {expected}"
                        )

    @staticmethod
    def _first_int_after(pattern: str, text: str) -> int | None:
        m = re.search(pattern, text, re.I)
        return int(m.group(1)) if m else None

    def _range(self, line: int, name: str, value: int | None, low: int, high: int) -> None:
        if value is not None and not low <= value <= high:
            self.add(line, "ERROR", "RANGE", f"{name} value {value} must be {low}..{high}")

    def _check_static_ranges(self) -> None:
        for bl in self.lines:
            text = _mask_strings(_strip_rem(bl.content))
            u = text.upper()

            self._range(bl.number, "BANK", self._first_int_after(r"\bBANK\s+(\d+)", u), 0, 15)
            self._range(bl.number, "GRAPHIC mode", self._first_int_after(r"\bGRAPHIC\s+(\d+)", u), 0, 5)
            self._range(bl.number, "VOL", self._first_int_after(r"\bVOL\s+(\d+)", u), 0, 15)
            self._range(bl.number, "TEMPO", self._first_int_after(r"\bTEMPO\s+(\d+)", u), 0, 255)

            for m in re.finditer(r"\bSPRITE\s+(\d+)", u):
                self._range(bl.number, "SPRITE number", int(m.group(1)), 1, 8)
            for m in re.finditer(r"\bMOVSPR\s+(\d+)", u):
                self._range(bl.number, "MOVSPR sprite", int(m.group(1)), 1, 8)
            for m in re.finditer(r"\bSOUND\s+(\d+)", u):
                self._range(bl.number, "SOUND voice", int(m.group(1)), 1, 3)
            for m in re.finditer(r"\bPOT\s*\(\s*(\d+)", u):
                self._range(bl.number, "POT paddle", int(m.group(1)), 1, 4)

            cm = re.search(r"\bCOLOR\s+(\d+)\s*,\s*(\d+)", u)
            if cm:
                self._range(bl.number, "COLOR source", int(cm.group(1)), 0, 6)
                self._range(bl.number, "COLOR value", int(cm.group(2)), 1, 16)

            # Validate literal POKE values only; expressions are intentionally left alone.
            for pm in re.finditer(r"\bPOKE\s+(\d+)\s*,\s*(\d+)", u):
                self._range(bl.number, "POKE address", int(pm.group(1)), 0, 65535)
                self._range(bl.number, "POKE value", int(pm.group(2)), 0, 255)

            wm = re.search(r"\bWINDOW\s+(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)", u)
            if wm:
                x1,y1,x2,y2 = map(int, wm.groups())
                for label, x in (("WINDOW left",x1),("WINDOW right",x2)):
                    self._range(bl.number, label, x, 0, 79)
                for label, y in (("WINDOW top",y1),("WINDOW bottom",y2)):
                    self._range(bl.number, label, y, 0, 24)

    def _check_interactive_commands(self) -> None:
        for bl in self.lines:
            u = _mask_strings(_strip_rem(bl.content)).upper()
            for command in INTERACTIVE_COMMANDS:
                if re.search(rf"(?<![A-Z]){command}(?![A-Z])", u):
                    self.add(
                        bl.number, "WARN", "INTERACTIVE_COMMAND",
                        f"{command} is primarily an interactive/program-editing command; verify use in stored program mode"
                    )

    def _extract_cfg_targets(self, bl: BasicLine) -> set[int]:
        text = _mask_strings(_strip_rem(bl.content)).upper()
        targets: set[int] = set()
        for m in re.finditer(r"\b(?:GOTO|GOSUB|GO\s+TO|THEN|ELSE)\s*(\d+)", text):
            targets.add(int(m.group(1)))
        m = re.search(r"\bON\b.+?\b(?:GOTO|GOSUB)\s+([^:]+)", text)
        if m:
            for value in m.group(1).split(","):
                if value.strip().isdigit():
                    targets.add(int(value.strip()))
        for m in re.finditer(r"\bCOLLISION\s+[123]\s*,\s*(\d+)", text):
            targets.add(int(m.group(1)))
        return {t for t in targets if t in self.line_map}

    def _check_reachability(self) -> None:
        if not self.lines:
            return

        numbers = [bl.number for bl in self.lines]
        index = {n: i for i, n in enumerate(numbers)}
        edges: dict[int, set[int]] = {n:set() for n in numbers}

        for bl in self.lines:
            n = bl.number
            i = index[n]
            text = _mask_strings(_strip_rem(bl.content)).upper().strip()
            targets = self._extract_cfg_targets(bl)
            edges[n].update(targets)

            has_next = i + 1 < len(numbers)
            next_line = numbers[i+1] if has_next else None

            # Only suppress fallthrough for a clearly unconditional final transfer/stop.
            statements = [s.strip().upper() for s in _split_statements(text) if s.strip()]
            last = statements[-1] if statements else ""
            unconditional = bool(
                re.match(r"^(?:GOTO|GO\s+TO)\s*\d+\s*$", last)
                or re.match(r"^(?:END|STOP)\s*$", last)
            )
            if has_next and not unconditional:
                edges[n].add(next_line)

        seen: set[int] = set()
        stack = [numbers[0]]
        while stack:
            n = stack.pop()
            if n in seen:
                continue
            seen.add(n)
            stack.extend(edges.get(n, ()))

        for n in numbers:
            if n not in seen:
                # DATA-only lines are intentionally reachable via READ/RESTORE semantics.
                content = self.line_map[n].content.strip().upper()
                if content.startswith("DATA"):
                    continue
                self.add(n, "WARN", "UNREACHABLE", "line appears unreachable in static control-flow analysis")


def check_source(source: str, reachability: bool = True) -> list[Issue]:
    checker = SyntaxChecker(reachability=reachability)
    checker.load(source)
    return checker.validate()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check Commodore 128 BASIC 7.0 .bas source.")
    parser.add_argument("filename")
    parser.add_argument("--json", action="store_true", help="machine-readable JSON output")
    parser.add_argument(
        "--no-reach", action="store_true",
        help="disable approximate unreachable-line warnings"
    )
    args = parser.parse_args(argv)

    try:
        source = Path(args.filename).read_text(encoding="utf-8")
    except OSError as exc:
        print(f"ERROR: cannot read {args.filename}: {exc}", file=sys.stderr)
        return 2

    env_no_reach = os.getenv("C128_NO_REACH", "").strip().lower() in {"1","true","yes","on"}
    issues = check_source(source, reachability=not (args.no_reach or env_no_reach))

    errors = sum(i.severity == "ERROR" for i in issues)
    warnings = sum(i.severity == "WARN" for i in issues)

    if args.json:
        print(json.dumps({
            "file": args.filename,
            "errors": errors,
            "warnings": warnings,
            "issues": [asdict(i) for i in issues],
        }, indent=2))
    else:
        for issue in issues:
            where = f"line {issue.line}" if issue.line is not None else "program"
            print(f"{issue.severity}: {where}: [{issue.code}] {issue.message}")
        print(f"{errors} ERROR(s), {warnings} WARNING(s)")

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
