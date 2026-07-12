#!/usr/bin/env python3

import math
import sys


class CalculatorError(Exception):
    pass


class Parser:
    def __init__(self, expression: str) -> None:
        self.expression = expression
        self.position = 0

    @staticmethod
    def is_digit(character: str) -> bool:
        return "0" <= character <= "9"

    @staticmethod
    def checked(value: float) -> float:
        if not math.isfinite(value):
            raise CalculatorError("non-finite result")
        return value

    def skip_whitespace(self) -> None:
        while self.position < len(self.expression) and self.expression[self.position] in " \t\r\n\v\f":
            self.position += 1

    def current(self) -> str | None:
        return self.expression[self.position] if self.position < len(self.expression) else None

    def parse(self) -> float:
        result = self.parse_add_sub()
        self.skip_whitespace()
        if self.position != len(self.expression):
            raise CalculatorError("trailing tokens")
        return self.checked(result)

    def parse_add_sub(self) -> float:
        value = self.parse_mul_div()
        while True:
            self.skip_whitespace()
            operation = self.current()
            if operation not in ("+", "-"):
                return value
            self.position += 1
            right = self.parse_mul_div()
            value = self.checked(value + right if operation == "+" else value - right)

    def parse_mul_div(self) -> float:
        value = self.parse_unary()
        while True:
            self.skip_whitespace()
            operation = self.current()
            if operation not in ("*", "/", "%"):
                return value
            self.position += 1
            right = self.parse_unary()
            if operation in ("/", "%") and right == 0.0:
                raise CalculatorError("division or remainder by zero")
            try:
                if operation == "*":
                    value = value * right
                elif operation == "/":
                    value = value / right
                else:
                    value = value % right
            except (ArithmeticError, ValueError, OverflowError) as error:
                raise CalculatorError("invalid arithmetic operation") from error
            value = self.checked(value)

    def parse_unary(self) -> float:
        self.skip_whitespace()
        operation = self.current()
        if operation in ("+", "-"):
            self.position += 1
            value = self.parse_unary()
            return self.checked(-value if operation == "-" else value)
        return self.parse_power()

    def parse_power(self) -> float:
        base = self.parse_primary()
        self.skip_whitespace()
        if self.current() != "^":
            return base
        self.position += 1
        exponent = self.parse_unary()
        try:
            return self.checked(math.pow(base, exponent))
        except (ValueError, OverflowError) as error:
            raise CalculatorError("invalid exponentiation") from error

    def parse_primary(self) -> float:
        self.skip_whitespace()
        if self.current() == "(":
            self.position += 1
            value = self.parse_add_sub()
            self.skip_whitespace()
            if self.current() != ")":
                raise CalculatorError("expected ')'")
            self.position += 1
            return value
        return self.parse_number()

    def parse_number(self) -> float:
        self.skip_whitespace()
        start = self.position
        while self.position < len(self.expression) and self.is_digit(self.expression[self.position]):
            self.position += 1
        digits_before = self.position > start

        digits_after = False
        if self.current() == ".":
            self.position += 1
            fraction_start = self.position
            while self.position < len(self.expression) and self.is_digit(self.expression[self.position]):
                self.position += 1
            digits_after = self.position > fraction_start
        if not digits_before and not digits_after:
            raise CalculatorError("expected number")

        if self.current() in ("e", "E"):
            self.position += 1
            if self.current() in ("+", "-"):
                self.position += 1
            exponent_start = self.position
            while self.position < len(self.expression) and self.is_digit(self.expression[self.position]):
                self.position += 1
            if self.position == exponent_start:
                raise CalculatorError("invalid exponent")

        token = self.expression[start:self.position]
        try:
            value = float(token)
        except ValueError as error:
            raise CalculatorError("invalid number") from error
        return self.checked(value)


def main() -> None:
    if len(sys.argv) != 2:
        raise CalculatorError("expected exactly one expression argument")
    result = Parser(sys.argv[1]).parse()
    print(format(result, ".17g"))


try:
    main()
except CalculatorError as error:
    print(f"error: {error or 'calculation failed'}", file=sys.stderr)
    sys.exit(1)
except Exception:
    print("error: calculation failed", file=sys.stderr)
    sys.exit(1)
