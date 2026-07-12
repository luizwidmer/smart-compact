#!/usr/bin/env python3
import math
import re
import sys


NUMBER = re.compile(r"(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?")


class ParseError(Exception):
    pass


class Parser:
    def __init__(self, source: str):
        self.source = source
        self.pos = 0

    def skip_space(self) -> None:
        while self.pos < len(self.source) and ord(self.source[self.pos]) < 128 and self.source[self.pos].isspace():
            self.pos += 1

    def take(self, character: str) -> bool:
        self.skip_space()
        if self.pos < len(self.source) and self.source[self.pos] == character:
            self.pos += 1
            return True
        return False

    def parse(self) -> float:
        result = self.parse_additive()
        self.skip_space()
        if self.pos != len(self.source):
            raise ParseError("trailing tokens")
        return result

    def parse_additive(self) -> float:
        result = self.parse_multiplicative()
        while True:
            if self.take("+"):
                result = self.checked(result + self.parse_multiplicative())
            elif self.take("-"):
                result = self.checked(result - self.parse_multiplicative())
            else:
                return result

    def parse_multiplicative(self) -> float:
        result = self.parse_unary()
        while True:
            if self.take("*"):
                result = self.checked(result * self.parse_unary())
            elif self.take("/"):
                right = self.parse_unary()
                if right == 0.0:
                    raise ParseError("division by zero")
                result = self.checked(result / right)
            elif self.take("%"):
                right = self.parse_unary()
                if right == 0.0:
                    raise ParseError("remainder by zero")
                result = self.checked(result % right)
            else:
                return result

    def parse_unary(self) -> float:
        if self.take("+"):
            return self.parse_unary()
        if self.take("-"):
            return self.checked(-self.parse_unary())
        return self.parse_power()

    def parse_power(self) -> float:
        result = self.parse_primary()
        if self.take("^"):
            exponent = self.parse_unary()
            result = self.checked(math.pow(result, exponent))
        return result

    def parse_primary(self) -> float:
        if self.take("("):
            result = self.parse_additive()
            if not self.take(")"):
                raise ParseError("expected ')'")
            return result

        self.skip_space()
        match = NUMBER.match(self.source, self.pos)
        if not match:
            raise ParseError("expected number or '('")
        self.pos = match.end()
        return self.checked(float(match.group(0)))

    @staticmethod
    def checked(value: float) -> float:
        if not math.isfinite(value):
            raise ParseError("non-finite result")
        return value


def main() -> int:
    if len(sys.argv) != 2:
        print("error: expected exactly one expression", file=sys.stderr)
        return 1
    try:
        print(repr(Parser(sys.argv[1]).parse()))
        return 0
    except (ParseError, ValueError, OverflowError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
