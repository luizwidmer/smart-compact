#!/usr/bin/env python3
import math
import re
import sys


NUMBER = re.compile(r"(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?")
ASCII_SPACE = " \t\n\r\v\f"


class ParseError(Exception):
    pass


class Parser:
    def __init__(self, text: str) -> None:
        self.text = text
        self.pos = 0

    def skip_space(self) -> None:
        while self.pos < len(self.text) and self.text[self.pos] in ASCII_SPACE:
            self.pos += 1

    def peek(self, token: str) -> bool:
        self.skip_space()
        return self.text.startswith(token, self.pos)

    def take(self, token: str) -> bool:
        if self.peek(token):
            self.pos += len(token)
            return True
        return False

    def expression(self) -> float:
        value = self.term()
        while True:
            if self.take("+"):
                value = self.checked(value + self.term())
            elif self.take("-"):
                value = self.checked(value - self.term())
            else:
                return value

    def term(self) -> float:
        value = self.unary()
        while True:
            if self.take("*"):
                value = self.checked(value * self.unary())
            elif self.take("/"):
                right = self.unary()
                if right == 0.0:
                    raise ParseError("division by zero")
                value = self.checked(value / right)
            elif self.take("%"):
                right = self.unary()
                if right == 0.0:
                    raise ParseError("remainder by zero")
                value = self.checked(value % right)
            else:
                return value

    def unary(self) -> float:
        if self.take("+"):
            return self.unary()
        if self.take("-"):
            return self.checked(-self.unary())
        return self.power()

    def power(self) -> float:
        value = self.primary()
        if self.take("^"):
            exponent = self.unary()
            try:
                value = math.pow(value, exponent)
            except (OverflowError, ValueError, ZeroDivisionError):
                raise ParseError("non-finite result") from None
            return self.checked(value)
        return value

    def primary(self) -> float:
        if self.take("("):
            value = self.expression()
            if not self.take(")"):
                raise ParseError("missing closing parenthesis")
            return value

        self.skip_space()
        match = NUMBER.match(self.text, self.pos)
        if not match:
            raise ParseError("expected number or parenthesis")
        self.pos = match.end()
        value = float(match.group())
        return self.checked(value)

    @staticmethod
    def checked(value: float) -> float:
        if not math.isfinite(value):
            raise ParseError("non-finite result")
        return value

    def parse(self) -> float:
        value = self.expression()
        self.skip_space()
        if self.pos != len(self.text):
            raise ParseError("trailing tokens")
        return self.checked(value)


def main() -> int:
    if len(sys.argv) != 2:
        print("error: expected exactly one expression argument", file=sys.stderr)
        return 2
    try:
        result = Parser(sys.argv[1]).parse()
        print(repr(result))
        return 0
    except (ParseError, ValueError):
        print("error: invalid expression", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
