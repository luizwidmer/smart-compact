#!/usr/bin/env python3
import math
import re
import sys


def fail(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    sys.exit(1)


class Parser:
    NUMBER_RE = re.compile(r"(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?")

    def __init__(self, text: str):
        self.text = text
        self.length = len(text)
        self.pos = 0

    def parse(self) -> float:
        value = self.parse_add_sub()
        self.skip_ws()
        if self.pos != self.length:
            fail("trailing input")
        return self.ensure_finite(value)

    def skip_ws(self) -> None:
        while self.pos < self.length and self.text[self.pos].isspace():
            self.pos += 1

    def parse_add_sub(self) -> float:
        value = self.parse_mul_div_mod()
        while True:
            self.skip_ws()
            if self.pos >= self.length:
                break
            ch = self.text[self.pos]
            if ch == "+":
                self.pos += 1
                right = self.parse_mul_div_mod()
                value = self.ensure_finite(value + right)
            elif ch == "-":
                self.pos += 1
                right = self.parse_mul_div_mod()
                value = self.ensure_finite(value - right)
            else:
                break
        return value

    def parse_mul_div_mod(self) -> float:
        value = self.parse_unary()
        while True:
            self.skip_ws()
            if self.pos >= self.length:
                break
            ch = self.text[self.pos]
            if ch == "*":
                self.pos += 1
                right = self.parse_unary()
                value = self.ensure_finite(value * right)
            elif ch == "/":
                self.pos += 1
                right = self.parse_unary()
                if right == 0.0:
                    fail("division by zero")
                value = self.ensure_finite(value / right)
            elif ch == "%":
                self.pos += 1
                right = self.parse_unary()
                if right == 0.0:
                    fail("remainder by zero")
                value = self.ensure_finite(value % right)
            else:
                break
        return value

    def parse_unary(self) -> float:
        self.skip_ws()
        if self.pos >= self.length:
            fail("malformed expression")
        ch = self.text[self.pos]
        if ch == "+":
            self.pos += 1
            return self.parse_unary()
        if ch == "-":
            self.pos += 1
            value = self.parse_unary()
            return self.ensure_finite(-value)
        return self.parse_pow()

    def parse_pow(self) -> float:
        value = self.parse_primary()
        self.skip_ws()
        if self.pos < self.length and self.text[self.pos] == "^":
            self.pos += 1
            right = self.parse_pow()
            value = self.ensure_finite(math.pow(value, right))
            return value
        return value

    def parse_primary(self) -> float:
        self.skip_ws()
        if self.pos >= self.length:
            fail("malformed expression")

        ch = self.text[self.pos]
        if ch == "(":
            self.pos += 1
            value = self.parse_add_sub()
            self.skip_ws()
            if self.pos >= self.length or self.text[self.pos] != ")":
                fail("missing closing parenthesis")
            self.pos += 1
            return value

        return self.parse_number()

    def parse_number(self) -> float:
        self.skip_ws()
        if self.pos >= self.length:
            fail("malformed expression")

        remainder = self.text[self.pos :]
        match = self.NUMBER_RE.match(remainder)
        if not match:
            fail("invalid token")

        token = match.group(0)
        self.pos += len(token)

        try:
            value = float(token)
        except ValueError:
            fail("invalid number")

        return self.ensure_finite(value)

    @staticmethod
    def ensure_finite(value: float) -> float:
        if not math.isfinite(value):
            fail("non-finite result")
        return value


def main() -> None:
    if len(sys.argv) != 2:
        fail("expected exactly one argument")

    expr = sys.argv[1]
    parser = Parser(expr)
    result = parser.parse()
    print(result)


if __name__ == "__main__":
    main()
