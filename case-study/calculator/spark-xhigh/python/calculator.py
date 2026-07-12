#!/usr/bin/env python3
import math
import re
import sys


class ParseError(Exception):
    pass


class Parser:
    NUMBER_RE = re.compile(r"(?:\d+\.\d*|\d+|\.\d+)(?:[eE][+-]?\d+)?")

    def __init__(self, expression: str):
        self.expression = expression
        self.pos = 0

    def parse(self) -> float:
        value = self.parse_expr()
        self.skip_ws()
        if self.pos != len(self.expression):
            raise ParseError("trailing input")
        return value

    def skip_ws(self) -> None:
        while self.pos < len(self.expression) and self.expression[self.pos].isspace():
            self.pos += 1

    def parse_expr(self) -> float:
        left = self.parse_term()
        while True:
            self.skip_ws()
            if self.pos >= len(self.expression):
                return left
            op = self.expression[self.pos]
            if op == "+":
                self.pos += 1
                right = self.parse_term()
                left = self.ensure_finite(left + right)
            elif op == "-":
                self.pos += 1
                right = self.parse_term()
                left = self.ensure_finite(left - right)
            else:
                return left

    def parse_term(self) -> float:
        left = self.parse_pow()
        while True:
            self.skip_ws()
            if self.pos >= len(self.expression):
                return left
            op = self.expression[self.pos]
            if op == "*":
                self.pos += 1
                right = self.parse_pow()
                left = self.ensure_finite(left * right)
            elif op == "/":
                self.pos += 1
                right = self.parse_pow()
                if right == 0.0:
                    raise ParseError("division by zero")
                left = self.ensure_finite(left / right)
            elif op == "%":
                self.pos += 1
                right = self.parse_pow()
                if right == 0.0:
                    raise ParseError("remainder by zero")
                left = self.ensure_finite(left % right)
            else:
                return left

    def parse_pow(self) -> float:
        left = self.parse_unary()
        self.skip_ws()
        if self.pos < len(self.expression) and self.expression[self.pos] == "^":
            self.pos += 1
            right = self.parse_pow()
            try:
                value = left ** right
            except (ValueError, OverflowError, ZeroDivisionError) as exc:
                raise ParseError("non-finite value") from exc
            return self.ensure_finite(value)
        return left

    def parse_unary(self) -> float:
        self.skip_ws()
        if self.pos >= len(self.expression):
            raise ParseError("unexpected end of input")
        ch = self.expression[self.pos]
        if ch == "+":
            self.pos += 1
            return self.parse_unary()
        if ch == "-":
            self.pos += 1
            return self.ensure_finite(-self.parse_unary())
        return self.parse_primary()

    def parse_primary(self) -> float:
        self.skip_ws()
        if self.pos >= len(self.expression):
            raise ParseError("unexpected end of input")
        ch = self.expression[self.pos]
        if ch == "(":
            self.pos += 1
            value = self.parse_expr()
            self.skip_ws()
            if self.pos >= len(self.expression) or self.expression[self.pos] != ")":
                raise ParseError("missing ')'")
            self.pos += 1
            return value
        if ch == "." or ch.isdigit():
            return self.parse_number()
        raise ParseError(f"unexpected token '{ch}'")

    def parse_number(self) -> float:
        self.skip_ws()
        if self.pos >= len(self.expression):
            raise ParseError("unexpected end of input")
        match = self.NUMBER_RE.match(self.expression, self.pos)
        if not match or match.start() != self.pos:
            raise ParseError("invalid number")
        token = match.group(0)
        self.pos = match.end()
        try:
            value = float(token)
        except ValueError as exc:
            raise ParseError("invalid number") from exc
        return self.ensure_finite(value)

    def ensure_finite(self, value: float) -> float:
        if not math.isfinite(value):
            raise ParseError("non-finite value")
        return value


def main() -> None:
    if len(sys.argv) != 2:
        print("error: expected exactly one expression argument", file=sys.stderr)
        sys.exit(1)

    try:
        parser = Parser(sys.argv[1])
        result = parser.parse()
    except ParseError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)

    print(repr(result), flush=True)


if __name__ == "__main__":
    main()
