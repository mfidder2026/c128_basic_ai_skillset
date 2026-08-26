#!/usr/bin/env python3
"""
bas2prg.py — Commodore 128 BASIC 7.0 text-to-PRG converter.

Targets native C128 mode / Commodore BASIC 7.0.

Key differences from a C64 BASIC V2 converter:
- Default BASIC load/start address is $1C01.
- BASIC 7.0 has one-byte tokens through $FD plus two extended token families:
  $CE xx for extended functions and $FE xx for extended statements.
- BASIC 7.0 keywords are recognized without requiring whitespace, just like the
  real Commodore tokenizer. Consequently variable names that contain keywords
  are unsafe and should be rejected by c128_syntax_checker.py.
- DATA contents are copied literally until the next colon outside quotes.
- REM contents are copied literally to end of line.

Recommended source convention:
    lowercase ASCII .bas source + invert_case=True / CLI -i

Example:
    python bas2prg.py demo.bas -o demo.prg -i

The generated PRG is a standard tokenized C128 BASIC program with load address
$1C01. It is intended for C128 mode, not C64 mode.
"""

from __future__ import annotations

import argparse
import struct
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

DEFAULT_START_ADDR = 0x1C01
DEFAULT_MAX_BASIC_ADDR = 0xFF00
MAX_LINE_NUMBER = 63999

# Commodore BASIC 2.0-compatible token block. BASIC 7.0 retains these tokens.
BASE_TOKENS: Sequence[tuple[str, bytes]] = (
    ("END", b"\x80"), ("FOR", b"\x81"), ("NEXT", b"\x82"),
    ("DATA", b"\x83"), ("INPUT#", b"\x84"), ("INPUT", b"\x85"),
    ("DIM", b"\x86"), ("READ", b"\x87"), ("LET", b"\x88"),
    ("GOTO", b"\x89"), ("RUN", b"\x8A"), ("IF", b"\x8B"),
    ("RESTORE", b"\x8C"), ("GOSUB", b"\x8D"), ("RETURN", b"\x8E"),
    ("REM", b"\x8F"), ("STOP", b"\x90"), ("ON", b"\x91"),
    ("WAIT", b"\x92"), ("LOAD", b"\x93"), ("SAVE", b"\x94"),
    ("VERIFY", b"\x95"), ("DEF", b"\x96"), ("POKE", b"\x97"),
    ("PRINT#", b"\x98"), ("PRINT", b"\x99"), ("CONT", b"\x9A"),
    ("LIST", b"\x9B"), ("CLR", b"\x9C"), ("CMD", b"\x9D"),
    ("SYS", b"\x9E"), ("OPEN", b"\x9F"), ("CLOSE", b"\xA0"),
    ("GET", b"\xA1"), ("NEW", b"\xA2"), ("TAB(", b"\xA3"),
    ("TO", b"\xA4"), ("FN", b"\xA5"), ("SPC(", b"\xA6"),
    ("THEN", b"\xA7"), ("NOT", b"\xA8"), ("STEP", b"\xA9"),
    ("+", b"\xAA"), ("-", b"\xAB"), ("*", b"\xAC"),
    ("/", b"\xAD"), ("^", b"\xAE"), ("AND", b"\xAF"),
    ("OR", b"\xB0"), (">", b"\xB1"), ("=", b"\xB2"),
    ("<", b"\xB3"), ("SGN", b"\xB4"), ("INT", b"\xB5"),
    ("ABS", b"\xB6"), ("USR", b"\xB7"), ("FRE", b"\xB8"),
    ("POS", b"\xB9"), ("SQR", b"\xBA"), ("RND", b"\xBB"),
    ("LOG", b"\xBC"), ("EXP", b"\xBD"), ("COS", b"\xBE"),
    ("SIN", b"\xBF"), ("TAN", b"\xC0"), ("ATN", b"\xC1"),
    ("PEEK", b"\xC2"), ("LEN", b"\xC3"), ("STR$", b"\xC4"),
    ("VAL", b"\xC5"), ("ASC", b"\xC6"), ("CHR$", b"\xC7"),
    ("LEFT$", b"\xC8"), ("RIGHT$", b"\xC9"), ("MID$", b"\xCA"),
    ("GO", b"\xCB"),
)

# BASIC 7.0 one-byte extension tokens.
ONE_BYTE_EXT_TOKENS: Sequence[tuple[str, bytes]] = (
    ("RGR", b"\xCC"), ("RCLR", b"\xCD"),
    # $CE is the extended-function escape byte.
    ("JOY", b"\xCF"), ("RDOT", b"\xD0"), ("DEC", b"\xD1"),
    ("HEX$", b"\xD2"), ("ERR$", b"\xD3"), ("INSTR", b"\xD4"),
    ("ELSE", b"\xD5"), ("RESUME", b"\xD6"), ("TRAP", b"\xD7"),
    ("TRON", b"\xD8"), ("TROFF", b"\xD9"), ("SOUND", b"\xDA"),
    ("VOL", b"\xDB"), ("AUTO", b"\xDC"), ("PUDEF", b"\xDD"),
    ("GRAPHIC", b"\xDE"), ("PAINT", b"\xDF"), ("CHAR", b"\xE0"),
    ("BOX", b"\xE1"), ("CIRCLE", b"\xE2"), ("GSHAPE", b"\xE3"),
    ("SSHAPE", b"\xE4"), ("DRAW", b"\xE5"), ("LOCATE", b"\xE6"),
    ("COLOR", b"\xE7"), ("SCNCLR", b"\xE8"), ("SCALE", b"\xE9"),
    ("HELP", b"\xEA"), ("DO", b"\xEB"), ("LOOP", b"\xEC"),
    ("EXIT", b"\xED"), ("DIRECTORY", b"\xEE"), ("DSAVE", b"\xEF"),
    ("DLOAD", b"\xF0"), ("HEADER", b"\xF1"), ("SCRATCH", b"\xF2"),
    ("COLLECT", b"\xF3"), ("COPY", b"\xF4"), ("RENAME", b"\xF5"),
    ("BACKUP", b"\xF6"), ("DELETE", b"\xF7"), ("RENUMBER", b"\xF8"),
    ("KEY", b"\xF9"), ("MONITOR", b"\xFA"), ("USING", b"\xFB"),
    ("UNTIL", b"\xFC"), ("WHILE", b"\xFD"),
    # $FE is the extended-statement escape byte.
)

# BASIC 7.0 extended functions: first byte $CE.
EXT_FUNCTION_TOKENS: Sequence[tuple[str, bytes]] = (
    ("POT", b"\xCE\x02"),
    ("BUMP", b"\xCE\x03"),
    ("PEN", b"\xCE\x04"),
    ("RSPPOS", b"\xCE\x05"),
    ("RSPRITE", b"\xCE\x06"),
    ("RSPCOLOR", b"\xCE\x07"),
    ("XOR", b"\xCE\x08"),
    ("RWINDOW", b"\xCE\x09"),
    ("POINTER", b"\xCE\x0A"),
)

# BASIC 7.0 extended statements: first byte $FE.
EXT_STATEMENT_TOKENS: Sequence[tuple[str, bytes]] = (
    ("BANK", b"\xFE\x02"),
    ("FILTER", b"\xFE\x03"),
    ("PLAY", b"\xFE\x04"),
    ("TEMPO", b"\xFE\x05"),
    ("MOVSPR", b"\xFE\x06"),
    ("SPRITE", b"\xFE\x07"),
    ("SPRCOLOR", b"\xFE\x08"),
    ("RREG", b"\xFE\x09"),
    ("ENVELOPE", b"\xFE\x0A"),
    ("SLEEP", b"\xFE\x0B"),
    ("CATALOG", b"\xFE\x0C"),
    ("DOPEN", b"\xFE\x0D"),
    ("APPEND", b"\xFE\x0E"),
    ("DCLOSE", b"\xFE\x0F"),
    ("BSAVE", b"\xFE\x10"),
    ("BLOAD", b"\xFE\x11"),
    ("RECORD", b"\xFE\x12"),
    ("CONCAT", b"\xFE\x13"),
    ("DVERIFY", b"\xFE\x14"),
    ("DCLEAR", b"\xFE\x15"),
    ("SPRSAV", b"\xFE\x16"),
    ("COLLISION", b"\xFE\x17"),
    ("BEGIN", b"\xFE\x18"),
    ("BEND", b"\xFE\x19"),
    ("WINDOW", b"\xFE\x1A"),
    ("BOOT", b"\xFE\x1B"),
    ("WIDTH", b"\xFE\x1C"),
    ("SPRDEF", b"\xFE\x1D"),
    ("QUIT", b"\xFE\x1E"),   # token exists; command is unimplemented on BASIC 7.0
    ("STASH", b"\xFE\x1F"),
    ("FETCH", b"\xFE\x21"),
    ("SWAP", b"\xFE\x23"),
    ("OFF", b"\xFE\x24"),    # token exists; command is unimplemented on BASIC 7.0
    ("FAST", b"\xFE\x25"),
    ("SLOW", b"\xFE\x26"),
)

# Public token list used by tests/tools.
TOKEN_PAIRS: Sequence[tuple[str, bytes]] = (
    BASE_TOKENS + ONE_BYTE_EXT_TOKENS + EXT_FUNCTION_TOKENS + EXT_STATEMENT_TOKENS
)

# Matching is deliberately not word-boundary based. The real Commodore tokenizer
# recognizes keywords even when no space follows them (FORI=..., GETKEY A$, GO64).
# Longest-first prevents shorter prefixes from stealing real longer keywords.
TOKEN_MATCH_ORDER: Sequence[tuple[str, bytes]] = tuple(
    sorted(TOKEN_PAIRS, key=lambda item: (-len(item[0]), item[0]))
)

TOKEN_BY_TEXT = {name: code for name, code in TOKEN_PAIRS}
TEXT_BY_TOKEN = {code: name for name, code in TOKEN_PAIRS}

REM_TOKEN = b"\x8F"
DATA_TOKEN = b"\x83"
PI_TOKEN = b"\xFF"

@dataclass(frozen=True)
class ParsedSourceLine:
    number: int
    content: str
    original: str


class Bas2PrgError(ValueError):
    """Raised for invalid source that cannot safely be encoded as BASIC 7.0."""


class Bas2Prg:
    def __init__(
        self,
        start_addr: int = DEFAULT_START_ADDR,
        invert_case: bool = False,
        auto_number: bool = False,
        trim_spaces: bool = False,
        collapse_spaces: bool = False,
        sort_lines: bool = True,
        max_basic_addr: int = DEFAULT_MAX_BASIC_ADDR,
    ) -> None:
        if not 0 <= start_addr <= 0xFFFF:
            raise Bas2PrgError("start_addr must be in range 0..65535")
        self.start_addr = start_addr
        self.invert_case = invert_case
        self.auto_number = auto_number
        self.trim_spaces = trim_spaces
        self.collapse_spaces = collapse_spaces
        self.sort_lines = sort_lines
        self.max_basic_addr = max_basic_addr

    @staticmethod
    def _ascii_swapcase(text: str) -> str:
        out: list[str] = []
        for ch in text:
            o = ord(ch)
            if 65 <= o <= 90:
                out.append(chr(o + 32))
            elif 97 <= o <= 122:
                out.append(chr(o - 32))
            else:
                out.append(ch)
        return "".join(out)

    @staticmethod
    def _encode_raw_char(ch: str) -> int:
        # ASCII byte values used by normal uppercase/graphics PETSCII source text
        # map directly for the common printable range. Keep conversion explicit.
        o = ord(ch)
        if o > 255:
            raise Bas2PrgError(
                f"character U+{o:04X} cannot be represented as a single PETSCII byte; "
                "use CHR$(n) in BASIC source"
            )
        return o

    @staticmethod
    def _find_token(text: str, pos: int) -> tuple[bytes | None, int, str | None]:
        # Special source notation for the pi token. ASCII 'PI' is NOT used,
        # because PI can otherwise be confused with normal variable text.
        if text.startswith("{PI}", pos):
            return PI_TOKEN, 4, "{PI}"
        if text.startswith("π", pos):
            return PI_TOKEN, 1, "π"

        fragment = text[pos:]
        for keyword, token in TOKEN_MATCH_ORDER:
            if fragment.startswith(keyword):
                return token, len(keyword), keyword
        return None, 0, None

    def _tokenize_line(self, content: str) -> bytes:
        output = bytearray()
        i = 0
        in_string = False
        rem_mode = False
        data_mode = False

        while i < len(content):
            ch = content[i]

            if rem_mode:
                output.append(self._encode_raw_char(ch))
                i += 1
                continue

            if data_mode:
                # DATA payload is literal until ':' outside a quoted string.
                if ch == '"':
                    in_string = not in_string
                    output.append(ord('"'))
                    i += 1
                    continue
                if ch == ':' and not in_string:
                    output.append(ord(':'))
                    data_mode = False
                    i += 1
                    continue
                output.append(self._encode_raw_char(ch))
                i += 1
                continue

            if ch == '"':
                in_string = not in_string
                output.append(ord('"'))
                i += 1
                continue

            if in_string:
                output.append(self._encode_raw_char(ch))
                i += 1
                continue

            if self.collapse_spaces and ch.isspace():
                i += 1
                continue

            token, token_len, keyword = self._find_token(content, i)
            if token is not None:
                output.extend(token)
                i += token_len
                if token == REM_TOKEN:
                    rem_mode = True
                elif token == DATA_TOKEN:
                    data_mode = True
                    in_string = False
                continue

            if ch != "\r":
                output.append(self._encode_raw_char(ch))
            i += 1

        if in_string:
            raise Bas2PrgError("unclosed quote in BASIC line")

        # A line with only a number is represented with a single blank statement
        # byte so that it remains a real BASIC line.
        if not output:
            output.append(ord(" "))

        output.append(0)
        return bytes(output)

    def _parse_source(self, source_text: str) -> list[ParsedSourceLine]:
        parsed: list[ParsedSourceLine] = []
        next_auto = 10

        for physical_line, raw in enumerate(source_text.splitlines(), start=1):
            if not raw.strip():
                continue

            line = self._ascii_swapcase(raw) if self.invert_case else raw
            stripped = line.lstrip()

            p = 0
            while p < len(stripped) and stripped[p].isdigit():
                p += 1

            if p == 0:
                if not self.auto_number:
                    raise Bas2PrgError(
                        f"physical line {physical_line}: missing BASIC line number"
                    )
                number = next_auto
                content = stripped
            else:
                number = int(stripped[:p])
                content = stripped[p:]
                # BASIC ignores formatting whitespace between the line number
                # and the first statement; remove it from generated program text.
                content = content.lstrip(" \t")
                next_auto = number + 10

            if not 0 <= number <= MAX_LINE_NUMBER:
                raise Bas2PrgError(
                    f"line {number}: BASIC 7.0 line number must be 0..{MAX_LINE_NUMBER}"
                )

            if self.trim_spaces:
                content = content.strip()

            parsed.append(ParsedSourceLine(number, content, raw))

        if self.sort_lines:
            parsed.sort(key=lambda line: line.number)

        seen: set[int] = set()
        previous = -1
        for line in parsed:
            if line.number in seen:
                raise Bas2PrgError(f"duplicate BASIC line number {line.number}")
            seen.add(line.number)
            if not self.sort_lines and line.number <= previous:
                raise Bas2PrgError(
                    f"line {line.number} is not strictly greater than previous line {previous}"
                )
            previous = line.number

        return parsed

    def convert(self, source_text: str) -> bytes:
        lines = self._parse_source(source_text)
        prg = bytearray(struct.pack("<H", self.start_addr))
        current_addr = self.start_addr

        for line in lines:
            tokenized = self._tokenize_line(line.content)
            # next-link + line-number + tokenized bytes including terminal NUL
            next_addr = current_addr + 4 + len(tokenized)

            if next_addr > 0xFFFF:
                raise Bas2PrgError(
                    f"program exceeds 16-bit address space at BASIC line {line.number}"
                )
            if self.max_basic_addr and next_addr >= self.max_basic_addr:
                raise Bas2PrgError(
                    f"program reaches ${next_addr:04X} at line {line.number}; "
                    f"standard C128 BASIC bank-0 text area ends below ${self.max_basic_addr:04X}"
                )

            prg.extend(struct.pack("<H", next_addr))
            prg.extend(struct.pack("<H", line.number))
            prg.extend(tokenized)
            current_addr = next_addr

        prg.extend(b"\x00\x00")
        return bytes(prg)


def iter_tokenized_program(prg: bytes) -> Iterable[tuple[int, bytes]]:
    """Yield (line_number, tokenized_content_without_NUL) from a generated PRG."""
    if len(prg) < 4:
        raise Bas2PrgError("PRG is too short")
    load_addr = struct.unpack_from("<H", prg, 0)[0]
    pos = 2
    current_addr = load_addr

    while True:
        if pos + 2 > len(prg):
            raise Bas2PrgError("truncated PRG link pointer")
        next_addr = struct.unpack_from("<H", prg, pos)[0]
        pos += 2
        if next_addr == 0:
            break
        if pos + 2 > len(prg):
            raise Bas2PrgError("truncated PRG line number")
        number = struct.unpack_from("<H", prg, pos)[0]
        pos += 2

        try:
            end = prg.index(0, pos)
        except ValueError as exc:
            raise Bas2PrgError("unterminated BASIC line") from exc
        content = prg[pos:end]
        yield number, content
        pos = end + 1

        expected = current_addr + 4 + len(content) + 1
        if next_addr != expected:
            raise Bas2PrgError(
                f"bad link on line {number}: ${next_addr:04X}, expected ${expected:04X}"
            )
        current_addr = next_addr


def token_hex(data: bytes) -> str:
    return " ".join(f"{b:02x}" for b in data)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Convert Commodore 128 BASIC 7.0 text source to tokenized PRG."
    )
    parser.add_argument("filename", nargs="?", help="input .bas file (stdin if omitted)")
    parser.add_argument("-o", "--output", help="output .prg file")
    parser.add_argument(
        "-i", "--invertcase", action="store_true",
        help="swap ASCII case before tokenization (recommended for lowercase source)"
    )
    parser.add_argument("-a", "--autonumber", action="store_true")
    parser.add_argument("-t", "--trimspaces", action="store_true")
    parser.add_argument("-c", "--collapsespaces", action="store_true")
    parser.add_argument(
        "-s", "--startaddr", default=f"0x{DEFAULT_START_ADDR:04x}",
        help="load/start address; default 0x1c01"
    )
    parser.add_argument(
        "--no-sort", action="store_true",
        help="preserve source order and reject nonascending line numbers"
    )
    parser.add_argument(
        "--dump", action="store_true",
        help="print line numbers and token bytes to stderr after conversion"
    )
    args = parser.parse_args(argv)

    try:
        start_addr = int(args.startaddr[1:], 16) if args.startaddr.startswith("$") else int(args.startaddr, 0)
    except ValueError:
        print(f"ERROR: invalid start address {args.startaddr!r}", file=sys.stderr)
        return 2

    if args.filename:
        try:
            source = Path(args.filename).read_text(encoding="utf-8")
        except OSError as exc:
            print(f"ERROR: cannot read {args.filename}: {exc}", file=sys.stderr)
            return 3
    else:
        source = sys.stdin.read()

    try:
        converter = Bas2Prg(
            start_addr=start_addr,
            invert_case=args.invertcase,
            auto_number=args.autonumber,
            trim_spaces=args.trimspaces,
            collapse_spaces=args.collapsespaces,
            sort_lines=not args.no_sort,
        )
        prg = converter.convert(source)
    except Bas2PrgError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.dump:
        print(f"load ${start_addr:04X}", file=sys.stderr)
        for number, body in iter_tokenized_program(prg):
            print(f"{number}: {token_hex(body)}", file=sys.stderr)

    if args.output:
        try:
            Path(args.output).write_bytes(prg)
        except OSError as exc:
            print(f"ERROR: cannot write {args.output}: {exc}", file=sys.stderr)
            return 4
    else:
        if sys.stdout.isatty():
            print("Binary PRG not written to terminal; use -o or redirect stdout.", file=sys.stderr)
            return 2
        sys.stdout.buffer.write(prg)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
