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
        while self.pos < len(self.text) and self.text[self.pos] in " \t\n\r\v\f":
            self.pos += 1

    def take(self, char: str) -> bool:
        self.skip_space()
        if self.pos < len(self.text) and self.text[self.pos] == char:
            self.pos += 1
            return True
        return False

    def parse(self) -> float:
        value = self.parse_additive()
        self.skip_space()
        if self.pos != len(self.text):
            raise CalculatorError("unexpected token")
        return value

    def parse_additive(self) -> float:
        value = self.parse_multiplicative()
        while True:
            if self.take("+"):
                value = checked(value + self.parse_multiplicative())
            elif self.take("-"):
                value = checked(value - self.parse_multiplicative())
            else:
                return value

    def parse_multiplicative(self) -> float:
        value = self.parse_unary()
        while True:
            if self.take("*"):
                value = checked(value * self.parse_unary())
            elif self.take("/"):
                divisor = self.parse_unary()
                if divisor == 0.0:
                    raise CalculatorError("division by zero")
                value = checked(value / divisor)
            elif self.take("%"):
                divisor = self.parse_unary()
                if divisor == 0.0:
                    raise CalculatorError("remainder by zero")
                value = checked(value % divisor)
            else:
                return value

    def parse_unary(self) -> float:
        if self.take("+"):
            return self.parse_unary()
        if self.take("-"):
            return checked(-self.parse_unary())
        return self.parse_power()

    def parse_power(self) -> float:
        value = self.parse_primary()
        if self.take("^"):
            exponent = self.parse_unary()
            try:
                value = math.pow(value, exponent)
            except (ValueError, OverflowError):
                raise CalculatorError("non-finite result")
            return checked(value)
        return value

    def parse_primary(self) -> float:
        if self.take("("):
            value = self.parse_additive()
            if not self.take(")"):
                raise CalculatorError("expected closing parenthesis")
            return value
        return self.parse_number()

    def parse_number(self) -> float:
        self.skip_space()
        start = self.pos
        before = 0
        while self.pos < len(self.text) and self.text[self.pos].isdigit() and self.text[self.pos].isascii():
            self.pos += 1
            before += 1
        after = 0
        if self.pos < len(self.text) and self.text[self.pos] == ".":
            self.pos += 1
            while self.pos < len(self.text) and self.text[self.pos].isdigit() and self.text[self.pos].isascii():
                self.pos += 1
                after += 1
        if before == 0 and after == 0:
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
        except ValueError:
            raise CalculatorError("invalid number")
        return checked(value)


def checked(value: float) -> float:
    if not math.isfinite(value):
        raise CalculatorError("non-finite result")
    return value


def main() -> int:
    if len(sys.argv) != 2:
        print("error: expected exactly one expression", file=sys.stderr)
        return 1
    try:
        print(repr(Parser(sys.argv[1]).parse()))
        return 0
    except CalculatorError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
