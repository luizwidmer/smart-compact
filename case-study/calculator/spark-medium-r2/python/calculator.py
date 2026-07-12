#!/usr/bin/env python3
import math
import sys


class Parser:
    def __init__(self, text: str):
        self.text = text
        self.len = len(text)
        self.pos = 0

    def parse(self) -> float:
        value = self.parse_expression()
        self.skip_ws()
        if self.pos != self.len:
            self.fail("unexpected trailing token")
        return self.ensure_finite(value)

    def parse_expression(self) -> float:
        value = self.parse_term()
        while True:
            self.skip_ws()
            if self.match('+'):
                value = self.ensure_finite(value + self.parse_term())
            elif self.match('-'):
                value = self.ensure_finite(value - self.parse_term())
            else:
                return value

    def parse_term(self) -> float:
        value = self.parse_power()
        while True:
            self.skip_ws()
            if self.match('*'):
                value = self.ensure_finite(value * self.parse_power())
            elif self.match('/'):
                rhs = self.parse_power()
                if rhs == 0:
                    self.fail("division by zero")
                value = self.ensure_finite(value / rhs)
            elif self.match('%'):
                rhs = self.parse_power()
                if rhs == 0:
                    self.fail("remainder by zero")
                value = self.ensure_finite(value % rhs)
            else:
                return value

    def parse_power(self) -> float:
        left = self.parse_unary()
        self.skip_ws()
        if self.match('^'):
            right = self.parse_power()
            try:
                value = left ** right
            except Exception:
                self.fail("result is not finite")
            return self.ensure_finite(value)
        return left

    def parse_unary(self) -> float:
        self.skip_ws()
        if self.match('+'):
            return self.parse_unary()
        if self.match('-'):
            return self.ensure_finite(-self.parse_unary())
        return self.parse_primary()

    def parse_primary(self) -> float:
        self.skip_ws()
        if self.match('('):
            value = self.parse_expression()
            self.skip_ws()
            if not self.match(')'):
                self.fail("missing closing parenthesis")
            return self.ensure_finite(value)
        return self.parse_number()

    def parse_number(self) -> float:
        self.skip_ws()
        start = self.pos

        if self.pos >= self.len:
            self.fail("expected number")

        if self.peek() == '.':
            self.pos += 1
            if self.pos >= self.len or not self.peek().isdigit():
                self.fail("invalid number")
            while self.pos < self.len and self.peek().isdigit():
                self.pos += 1
        elif self.peek().isdigit():
            while self.pos < self.len and self.peek().isdigit():
                self.pos += 1
            if self.pos < self.len and self.peek() == '.':
                self.pos += 1
                while self.pos < self.len and self.peek().isdigit():
                    self.pos += 1
        else:
            self.fail("invalid number")

        if self.pos < self.len and self.peek() in 'eE':
            self.pos += 1
            if self.pos < self.len and self.peek() in '+-':
                self.pos += 1
            if self.pos >= self.len or not self.peek().isdigit():
                self.fail("invalid scientific notation")
            while self.pos < self.len and self.peek().isdigit():
                self.pos += 1

        token = self.text[start:self.pos]
        try:
            value = float(token)
        except ValueError:
            self.fail("invalid number")

        return self.ensure_finite(value)

    def ensure_finite(self, value: float) -> float:
        if not math.isfinite(value):
            self.fail("result is not finite")
        return value

    def skip_ws(self):
        while self.pos < self.len and self.text[self.pos].isspace():
            self.pos += 1

    def match(self, ch: str) -> bool:
        if self.pos < self.len and self.text[self.pos] == ch:
            self.pos += 1
            return True
        return False

    def peek(self) -> str:
        return self.text[self.pos]

    def fail(self, msg: str):
        print(f"error: {msg}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    if len(sys.argv) != 2:
        print("error: expected one expression argument", file=sys.stderr)
        sys.exit(1)

    value = Parser(sys.argv[1]).parse()
    print(repr(value))


if __name__ == '__main__':
    main()
