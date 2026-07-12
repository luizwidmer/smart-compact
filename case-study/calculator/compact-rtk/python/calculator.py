#!/usr/bin/env python3

import math
import sys


class CalculatorError(Exception):
    pass


class Parser:
    def __init__(self, text: str) -> None:
        self.text = text
        self.pos = 0

    def skip_whitespace(self) -> None:
        while self.pos < len(self.text) and self.text[self.pos] in " \t\n\r\f\v":
            self.pos += 1

    def consume(self, token: str) -> bool:
        self.skip_whitespace()
        if self.pos < len(self.text) and self.text[self.pos] == token:
            self.pos += 1
            return True
        return False

    @staticmethod
    def checked(value: float) -> float:
        if not math.isfinite(value):
            raise CalculatorError("non-finite result")
        return value

    def parse(self) -> float:
        value = self.expression()
        self.skip_whitespace()
        if self.pos != len(self.text):
            raise CalculatorError("unexpected trailing input")
        return value

    def expression(self) -> float:
        value = self.term()
        while True:
            if self.consume("+"):
                value = self.checked(value + self.term())
            elif self.consume("-"):
                value = self.checked(value - self.term())
            else:
                return value

    def term(self) -> float:
        value = self.unary()
        while True:
            if self.consume("*"):
                value = self.checked(value * self.unary())
            elif self.consume("/"):
                divisor = self.unary()
                if divisor == 0.0:
                    raise CalculatorError("division by zero")
                value = self.checked(value / divisor)
            elif self.consume("%"):
                divisor = self.unary()
                if divisor == 0.0:
                    raise CalculatorError("remainder by zero")
                value = self.checked(value % divisor)
            else:
                return value

    def unary(self) -> float:
        if self.consume("+"):
            return self.checked(+self.unary())
        if self.consume("-"):
            return self.checked(-self.unary())
        return self.power()

    def power(self) -> float:
        base = self.primary()
        if self.consume("^"):
            exponent = self.unary()
            try:
                return self.checked(math.pow(base, exponent))
            except (OverflowError, ValueError) as exc:
                raise CalculatorError("invalid exponentiation") from exc
        return base

    def primary(self) -> float:
        if self.consume("("):
            value = self.expression()
            if not self.consume(")"):
                raise CalculatorError("expected ')'")
            return value
        return self.number()

    def number(self) -> float:
        self.skip_whitespace()
        start = self.pos
        digits_before = 0
        while self.pos < len(self.text) and self.text[self.pos].isdigit() and self.text[self.pos].isascii():
            self.pos += 1
            digits_before += 1

        digits_after = 0
        if self.pos < len(self.text) and self.text[self.pos] == ".":
            self.pos += 1
            while self.pos < len(self.text) and self.text[self.pos].isdigit() and self.text[self.pos].isascii():
                self.pos += 1
                digits_after += 1

        if digits_before + digits_after == 0:
            raise CalculatorError("expected number")

        if self.pos < len(self.text) and self.text[self.pos] in "eE":
            self.pos += 1
            if self.pos < len(self.text) and self.text[self.pos] in "+-":
                self.pos += 1
            exponent_start = self.pos
            while self.pos < len(self.text) and self.text[self.pos].isdigit() and self.text[self.pos].isascii():
                self.pos += 1
            if self.pos == exponent_start:
                raise CalculatorError("malformed exponent")

        try:
            value = float(self.text[start:self.pos])
        except ValueError as exc:
            raise CalculatorError("invalid number") from exc
        return self.checked(value)


def main() -> int:
    if len(sys.argv) != 2:
        print("error: expected exactly one expression argument", file=sys.stderr)
        return 1
    try:
        result = Parser(sys.argv[1]).parse()
        print(format(result, ".17g"))
        return 0
    except CalculatorError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
