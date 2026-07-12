#!/usr/bin/env python3
import math
import sys
from dataclasses import dataclass


@dataclass
class Parser:
    s: str
    i: int = 0
    n: int = 0

    def __post_init__(self):
        self.n = len(self.s)

    def skip_ws(self):
        while self.i < self.n and self.s[self.i].isspace():
            self.i += 1

    def parse_number(self) -> float:
        self.skip_ws()
        start = self.i
        has_digit = False

        if self.i < self.n and self.s[self.i] == '.':
            self.i += 1
            while self.i < self.n and self.s[self.i].isdigit():
                self.i += 1
                has_digit = True
        else:
            while self.i < self.n and self.s[self.i].isdigit():
                self.i += 1
                has_digit = True
            if self.i < self.n and self.s[self.i] == '.':
                self.i += 1
                while self.i < self.n and self.s[self.i].isdigit():
                    self.i += 1
                    has_digit = True

        if not has_digit:
            raise ValueError("invalid number")

        if self.i < self.n and self.s[self.i] in 'eE':
            self.i += 1
            if self.i < self.n and self.s[self.i] in '+-':
                self.i += 1
            if self.i >= self.n or not self.s[self.i].isdigit():
                raise ValueError("invalid exponent")
            while self.i < self.n and self.s[self.i].isdigit():
                self.i += 1

        token = self.s[start:self.i]
        value = float(token)
        if not math.isfinite(value):
            raise OverflowError("non-finite number")
        return value

    def parse_expr(self) -> float:
        value = self.parse_term()
        while True:
            self.skip_ws()
            if self.i >= self.n:
                return value
            ch = self.s[self.i]
            if ch not in '+-':
                return value
            self.i += 1
            rhs = self.parse_term()
            if ch == '+':
                value += rhs
            else:
                value -= rhs

    def parse_term(self) -> float:
        value = self.parse_power()
        while True:
            self.skip_ws()
            if self.i >= self.n:
                return value
            ch = self.s[self.i]
            if ch not in '*/%':
                return value
            self.i += 1
            rhs = self.parse_power()
            if ch == '*':
                value *= rhs
            elif ch == '/':
                if rhs == 0.0:
                    raise ZeroDivisionError("division by zero")
                value /= rhs
            else:
                if rhs == 0.0:
                    raise ZeroDivisionError("remainder by zero")
                value %= rhs

            if not math.isfinite(value):
                raise OverflowError("non-finite result")

    def parse_power(self) -> float:
        value = self.parse_unary()
        self.skip_ws()
        if self.i >= self.n or self.s[self.i] != '^':
            return value
        self.i += 1
        rhs = self.parse_power()
        value = value ** rhs
        if not math.isfinite(value):
            raise OverflowError("non-finite result")
        return value

    def parse_unary(self) -> float:
        self.skip_ws()
        if self.i < self.n and self.s[self.i] in '+-':
            op = self.s[self.i]
            self.i += 1
            value = self.parse_unary()
            return -value if op == '-' else value
        return self.parse_primary()

    def parse_primary(self) -> float:
        self.skip_ws()
        if self.i >= self.n:
            raise ValueError("unexpected end")
        if self.s[self.i] == '(':
            self.i += 1
            value = self.parse_expr()
            self.skip_ws()
            if self.i >= self.n or self.s[self.i] != ')':
                raise ValueError("missing )")
            self.i += 1
            return value
        return self.parse_number()


def evaluate(expr: str) -> float:
    p = Parser(expr)
    p.skip_ws()
    if p.i >= p.n:
        raise ValueError("empty expression")
    value = p.parse_expr()
    p.skip_ws()
    if p.i != p.n:
        raise ValueError("trailing token")
    if not math.isfinite(value):
        raise OverflowError("non-finite result")
    return value


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        sys.stderr.write("error: expected exactly one expression\n")
        return 1

    try:
        value = evaluate(argv[1])
        sys.stdout.write(repr(value) + "\n")
        return 0
    except Exception as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
