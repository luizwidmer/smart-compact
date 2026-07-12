#!/usr/bin/env python3
import math
import sys


class ParseError(Exception):
    pass


class Parser:
    def __init__(self, source: str):
        self.source = source
        self.pos = 0

    def skip_space(self) -> None:
        while self.pos < len(self.source) and self.source[self.pos] in " \t\n\r\v\f":
            self.pos += 1

    def fail(self, message: str) -> None:
        raise ParseError(message)

    def parse_number(self) -> float:
        self.skip_space()
        start = self.pos
        digits_before = 0
        while self.pos < len(self.source) and self.source[self.pos].isdigit() and self.source[self.pos].isascii():
            self.pos += 1
            digits_before += 1
        digits_after = 0
        if self.pos < len(self.source) and self.source[self.pos] == ".":
            self.pos += 1
            while self.pos < len(self.source) and self.source[self.pos].isdigit() and self.source[self.pos].isascii():
                self.pos += 1
                digits_after += 1
        if digits_before + digits_after == 0:
            self.fail("expected number")
        if self.pos < len(self.source) and self.source[self.pos] in "eE":
            self.pos += 1
            if self.pos < len(self.source) and self.source[self.pos] in "+-":
                self.pos += 1
            exponent_start = self.pos
            while self.pos < len(self.source) and self.source[self.pos].isdigit() and self.source[self.pos].isascii():
                self.pos += 1
            if self.pos == exponent_start:
                self.fail("invalid exponent")
        try:
            value = float(self.source[start:self.pos])
        except ValueError:
            self.fail("invalid number")
        if not math.isfinite(value):
            self.fail("non-finite number")
        return value

    def parse_primary(self) -> float:
        self.skip_space()
        if self.pos < len(self.source) and self.source[self.pos] == "(":
            self.pos += 1
            value = self.parse_additive()
            self.skip_space()
            if self.pos >= len(self.source) or self.source[self.pos] != ")":
                self.fail("expected ')'")
            self.pos += 1
            return value
        return self.parse_number()

    def parse_power(self) -> float:
        value = self.parse_primary()
        self.skip_space()
        if self.pos < len(self.source) and self.source[self.pos] == "^":
            self.pos += 1
            exponent = self.parse_unary()
            try:
                value = value ** exponent
            except (OverflowError, ZeroDivisionError, ValueError, TypeError):
                self.fail("invalid power")
            if not math.isfinite(value):
                self.fail("non-finite result")
        return value

    def parse_unary(self) -> float:
        self.skip_space()
        if self.pos < len(self.source) and self.source[self.pos] in "+-":
            sign = self.source[self.pos]
            self.pos += 1
            value = self.parse_unary()
            return value if sign == "+" else -value
        return self.parse_power()

    def parse_multiplicative(self) -> float:
        value = self.parse_unary()
        while True:
            self.skip_space()
            if self.pos >= len(self.source) or self.source[self.pos] not in "*/%":
                return value
            operator = self.source[self.pos]
            self.pos += 1
            right = self.parse_unary()
            if right == 0.0:
                self.fail("division by zero")
            try:
                value = value * right if operator == "*" else value / right if operator == "/" else value % right
            except (OverflowError, ZeroDivisionError, ValueError):
                self.fail("invalid arithmetic")
            if not math.isfinite(value):
                self.fail("non-finite result")

    def parse_additive(self) -> float:
        value = self.parse_multiplicative()
        while True:
            self.skip_space()
            if self.pos >= len(self.source) or self.source[self.pos] not in "+-":
                return value
            operator = self.source[self.pos]
            self.pos += 1
            right = self.parse_multiplicative()
            value = value + right if operator == "+" else value - right
            if not math.isfinite(value):
                self.fail("non-finite result")

    def parse(self) -> float:
        value = self.parse_additive()
        self.skip_space()
        if self.pos != len(self.source):
            self.fail("unexpected token")
        return value


def main() -> int:
    if len(sys.argv) != 2:
        print("error: expected exactly one expression", file=sys.stderr)
        return 1
    try:
        result = Parser(sys.argv[1]).parse()
    except ParseError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(repr(result))
    return 0


raise SystemExit(main())
