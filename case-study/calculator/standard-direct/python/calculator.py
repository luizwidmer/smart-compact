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

    def consume(self, token: str) -> bool:
        self.skip_space()
        if self.pos < len(self.text) and self.text[self.pos] == token:
            self.pos += 1
            return True
        return False

    @staticmethod
    def finite(value: float) -> float:
        if not math.isfinite(value):
            raise CalculatorError("non-finite result")
        return value

    def parse(self) -> float:
        value = self.parse_additive()
        self.skip_space()
        if self.pos != len(self.text):
            raise CalculatorError("unexpected trailing input")
        return value

    def parse_additive(self) -> float:
        value = self.parse_multiplicative()
        while True:
            if self.consume("+"):
                value = self.finite(value + self.parse_multiplicative())
            elif self.consume("-"):
                value = self.finite(value - self.parse_multiplicative())
            else:
                return value

    def parse_multiplicative(self) -> float:
        value = self.parse_unary()
        while True:
            if self.consume("*"):
                value = self.finite(value * self.parse_unary())
            elif self.consume("/"):
                divisor = self.parse_unary()
                if divisor == 0.0:
                    raise CalculatorError("division by zero")
                value = self.finite(value / divisor)
            elif self.consume("%"):
                divisor = self.parse_unary()
                if divisor == 0.0:
                    raise CalculatorError("remainder by zero")
                value = self.finite(math.fmod(value, divisor))
            else:
                return value

    def parse_unary(self) -> float:
        if self.consume("+"):
            return self.parse_unary()
        if self.consume("-"):
            return self.finite(-self.parse_unary())
        return self.parse_power()

    def parse_power(self) -> float:
        value = self.parse_primary()
        if self.consume("^"):
            try:
                value = math.pow(value, self.parse_unary())
            except (ValueError, OverflowError):
                raise CalculatorError("invalid exponentiation") from None
            return self.finite(value)
        return value

    def parse_primary(self) -> float:
        if self.consume("("):
            value = self.parse_additive()
            if not self.consume(")"):
                raise CalculatorError("expected closing parenthesis")
            return value
        return self.parse_number()

    def parse_number(self) -> float:
        self.skip_space()
        start = self.pos
        digits = 0
        while self.pos < len(self.text) and self.text[self.pos].isdigit() and self.text[self.pos].isascii():
            self.pos += 1
            digits += 1
        if self.pos < len(self.text) and self.text[self.pos] == ".":
            self.pos += 1
            while self.pos < len(self.text) and self.text[self.pos].isdigit() and self.text[self.pos].isascii():
                self.pos += 1
                digits += 1
        if digits == 0:
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
            return self.finite(float(self.text[start:self.pos]))
        except ValueError:
            raise CalculatorError("invalid number") from None


def main() -> int:
    if len(sys.argv) != 2:
        print("error: expected exactly one expression argument", file=sys.stderr)
        return 1
    try:
        result = Parser(sys.argv[1]).parse()
    except CalculatorError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(format(result, ".17g"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
