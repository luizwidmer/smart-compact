#!/usr/bin/env python3
import math
import sys


def error(msg: str) -> None:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def parse_number(text: str, start: int):
    n = len(text)
    j = start

    if j >= n:
        return None, start

    has_digit = False

    if text[j] == ".":
        j += 1
        if j < n and text[j].isdigit():
            has_digit = True
            while j < n and text[j].isdigit():
                j += 1
        else:
            return None, start
    elif text[j].isdigit():
        while j < n and text[j].isdigit():
            j += 1
            has_digit = True
        if j < n and text[j] == ".":
            j += 1
            while j < n and text[j].isdigit():
                j += 1
    else:
        return None, start

    if j < n and text[j] in "eE":
        j += 1
        if j < n and text[j] in "+-":
            j += 1
        if j >= n or not text[j].isdigit():
            return None, start
        while j < n and text[j].isdigit():
            j += 1

    if not has_digit:
        return None, start

    token = text[start:j]
    try:
        return float(token), j
    except ValueError:
        return None, start


class Parser:
    def __init__(self, text: str):
        self.text = text
        self.n = len(text)
        self.i = 0

    def skip_ws(self):
        while self.i < self.n and self.text[self.i].isspace():
            self.i += 1

    def parse(self) -> float:
        v = self.parse_expr()
        self.skip_ws()
        if self.i != self.n:
            error("unexpected token")
        if not math.isfinite(v):
            error("non-finite result")
        return v

    def parse_expr(self) -> float:
        v = self.parse_term()
        while True:
            self.skip_ws()
            if self.i >= self.n:
                break
            op = self.text[self.i]
            if op not in "+-":
                break
            self.i += 1
            rhs = self.parse_term()
            v = v + rhs if op == "+" else v - rhs
            if not math.isfinite(v):
                error("non-finite result")
        return v

    def parse_term(self) -> float:
        v = self.parse_unary()
        while True:
            self.skip_ws()
            if self.i >= self.n:
                break
            op = self.text[self.i]
            if op not in "*/%":
                break
            self.i += 1
            rhs = self.parse_unary()
            if op == "/":
                if rhs == 0.0:
                    error("division by zero")
                v = v / rhs
            elif op == "%":
                if rhs == 0.0:
                    error("remainder by zero")
                v = v % rhs
            else:
                v = v * rhs
            if not math.isfinite(v):
                error("non-finite result")
        return v

    def parse_unary(self) -> float:
        self.skip_ws()
        if self.i >= self.n:
            error("unexpected end of input")
        if self.text[self.i] == "+":
            self.i += 1
            return self.parse_unary()
        if self.text[self.i] == "-":
            self.i += 1
            return -self.parse_unary()
        return self.parse_power()

    def parse_power(self) -> float:
        v = self.parse_primary()
        self.skip_ws()
        if self.i < self.n and self.text[self.i] == "^":
            self.i += 1
            rhs = self.parse_unary()
            if v == 0.0 and rhs < 0:
                error("non-finite result")
            try:
                v = v ** rhs
            except Exception:
                error("non-finite result")
            if not math.isfinite(v):
                error("non-finite result")
        return v

    def parse_primary(self) -> float:
        self.skip_ws()
        if self.i >= self.n:
            error("unexpected end of input")

        if self.text[self.i] == "(":
            self.i += 1
            v = self.parse_expr()
            self.skip_ws()
            if self.i >= self.n or self.text[self.i] != ")":
                error("missing closing parenthesis")
            self.i += 1
            return v

        value, j = parse_number(self.text, self.i)
        if value is None:
            error("invalid number")
        self.i = j
        return value


def main() -> None:
    if len(sys.argv) != 2:
        error("usage: calculator <expression>")

    parser = Parser(sys.argv[1])
    result = parser.parse()
    if not math.isfinite(result):
        error("non-finite result")

    if result == int(result):
        print(int(result))
    else:
        print(repr(result))


if __name__ == "__main__":
    main()
