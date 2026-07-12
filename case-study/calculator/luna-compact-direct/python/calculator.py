#!/usr/bin/env python3

import math
import sys


class CalculatorError(Exception):
    pass


class ExpressionParser:
    def __init__(self, source: str):
        self.source = source
        self.index = 0

    def skip_whitespace(self) -> None:
        while self.index < len(self.source) and self.source[self.index] in " \t\n\r\v\f":
            self.index += 1

    def take(self, character: str) -> bool:
        self.skip_whitespace()
        if self.index < len(self.source) and self.source[self.index] == character:
            self.index += 1
            return True
        return False

    @staticmethod
    def finite(value: float) -> float:
        if not math.isfinite(value):
            raise CalculatorError("non-finite result")
        return value

    def evaluate(self) -> float:
        result = self.parse_sum()
        self.skip_whitespace()
        if self.index != len(self.source):
            raise CalculatorError("unexpected trailing input")
        return result

    def parse_sum(self) -> float:
        result = self.parse_product()
        while True:
            if self.take("+"):
                result = self.finite(result + self.parse_product())
            elif self.take("-"):
                result = self.finite(result - self.parse_product())
            else:
                return result

    def parse_product(self) -> float:
        result = self.parse_unary()
        while True:
            if self.take("*"):
                result = self.finite(result * self.parse_unary())
            elif self.take("/"):
                divisor = self.parse_unary()
                if divisor == 0.0:
                    raise CalculatorError("division by zero")
                result = self.finite(result / divisor)
            elif self.take("%"):
                divisor = self.parse_unary()
                if divisor == 0.0:
                    raise CalculatorError("remainder by zero")
                try:
                    result = self.finite(math.fmod(result, divisor))
                except ValueError:
                    raise CalculatorError("invalid remainder") from None
            else:
                return result

    def parse_unary(self) -> float:
        if self.take("+"):
            return self.parse_unary()
        if self.take("-"):
            return self.finite(-self.parse_unary())
        return self.parse_power()

    def parse_power(self) -> float:
        base = self.parse_primary()
        if self.take("^"):
            exponent = self.parse_unary()
            try:
                return self.finite(math.pow(base, exponent))
            except (OverflowError, ValueError, ZeroDivisionError):
                raise CalculatorError("invalid exponentiation") from None
        return base

    def parse_primary(self) -> float:
        if self.take("("):
            result = self.parse_sum()
            if not self.take(")"):
                raise CalculatorError("expected closing parenthesis")
            return result
        return self.parse_number()

    def parse_number(self) -> float:
        self.skip_whitespace()
        start = self.index
        digit_count = 0

        while self.index < len(self.source) and "0" <= self.source[self.index] <= "9":
            self.index += 1
            digit_count += 1

        if self.index < len(self.source) and self.source[self.index] == ".":
            self.index += 1
            while self.index < len(self.source) and "0" <= self.source[self.index] <= "9":
                self.index += 1
                digit_count += 1

        if digit_count == 0:
            raise CalculatorError("expected number")

        if self.index < len(self.source) and self.source[self.index] in "eE":
            self.index += 1
            if self.index < len(self.source) and self.source[self.index] in "+-":
                self.index += 1
            exponent_start = self.index
            while self.index < len(self.source) and "0" <= self.source[self.index] <= "9":
                self.index += 1
            if self.index == exponent_start:
                raise CalculatorError("malformed exponent")

        token = self.source[start:self.index]
        try:
            return self.finite(float(token))
        except ValueError:
            raise CalculatorError("invalid number") from None


def main() -> int:
    if len(sys.argv) != 2:
        print("error: expected exactly one expression argument", file=sys.stderr)
        return 1
    try:
        result = ExpressionParser(sys.argv[1]).evaluate()
    except CalculatorError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(format(result, ".17g"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
