#!/usr/bin/env python3

import math
import sys


class CalculatorError(Exception):
    pass


class Parser:
    def __init__(self, text: str):
        self.text = text
        self.pos = 0

    def skip_space(self) -> None:
        while self.pos < len(self.text) and self.text[self.pos] in " \t\n\r\f\v":
            self.pos += 1

    def take(self, token: str) -> bool:
        self.skip_space()
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
        value = self.additive()
        self.skip_space()
        if self.pos != len(self.text):
            raise CalculatorError("unexpected trailing input")
        return value

    def additive(self) -> float:
        value = self.multiplicative()
        while True:
            if self.take("+"):
                value = self.checked(value + self.multiplicative())
            elif self.take("-"):
                value = self.checked(value - self.multiplicative())
            else:
                return value

    def multiplicative(self) -> float:
        value = self.unary()
        while True:
            if self.take("*"):
                value = self.checked(value * self.unary())
            elif self.take("/"):
                divisor = self.unary()
                if divisor == 0.0:
                    raise CalculatorError("division by zero")
                value = self.checked(value / divisor)
            elif self.take("%"):
                divisor = self.unary()
                if divisor == 0.0:
                    raise CalculatorError("remainder by zero")
                value = self.checked(value % divisor)
            else:
                return value

    def unary(self) -> float:
        if self.take("+"):
            return self.unary()
        if self.take("-"):
            return self.checked(-self.unary())
        return self.power()

    def power(self) -> float:
        base = self.primary()
        if self.take("^"):
            exponent = self.unary()
            try:
                return self.checked(math.pow(base, exponent))
            except (ValueError, OverflowError) as exc:
                raise CalculatorError("invalid exponentiation") from exc
        return base

    def primary(self) -> float:
        if self.take("("):
            value = self.additive()
            if not self.take(")"):
                raise CalculatorError("expected ')'")
            return value
        return self.number()

    def number(self) -> float:
        self.skip_space()
        start = self.pos
        digits = 0
        while self.pos < len(self.text) and "0" <= self.text[self.pos] <= "9":
            self.pos += 1
            digits += 1
        if self.pos < len(self.text) and self.text[self.pos] == ".":
            self.pos += 1
            while self.pos < len(self.text) and "0" <= self.text[self.pos] <= "9":
                self.pos += 1
                digits += 1
        if digits == 0:
            raise CalculatorError("expected number")
        if self.pos < len(self.text) and self.text[self.pos] in "eE":
            self.pos += 1
            if self.pos < len(self.text) and self.text[self.pos] in "+-":
                self.pos += 1
            exponent_start = self.pos
            while self.pos < len(self.text) and "0" <= self.text[self.pos] <= "9":
                self.pos += 1
            if self.pos == exponent_start:
                raise CalculatorError("malformed exponent")
        try:
            value = float(self.text[start:self.pos])
        except ValueError as exc:
            raise CalculatorError("invalid number") from exc
        if not math.isfinite(value):
            raise CalculatorError("non-finite input")
        return value


def main() -> int:
    if len(sys.argv) != 2:
        print("error: expected exactly one expression", file=sys.stderr)
        return 1
    try:
        result = Parser(sys.argv[1]).parse()
    except CalculatorError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(repr(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
