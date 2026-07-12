#!/usr/bin/env python3

import math
import sys


class CalcError(Exception):
    pass


def is_ascii_whitespace(character: str) -> bool:
    code = ord(character)
    return 9 <= code <= 13 or code == 32


class Parser:
    def __init__(self, text: str) -> None:
        self.text = text
        self.position = 0

    def skip_whitespace(self) -> None:
        while self.position < len(self.text) and is_ascii_whitespace(
            self.text[self.position]
        ):
            self.position += 1

    def peek(self) -> str | None:
        if self.position >= len(self.text):
            return None
        return self.text[self.position]

    @staticmethod
    def checked(value: float, message: str = "non-finite result") -> float:
        if not math.isfinite(value):
            raise CalcError(message)
        return value

    def parse(self) -> float:
        value = self.parse_additive()
        self.skip_whitespace()
        if self.position != len(self.text):
            raise CalcError("unexpected trailing token")
        return self.checked(value)

    def parse_additive(self) -> float:
        value = self.parse_multiplicative()
        while True:
            self.skip_whitespace()
            operator = self.peek()
            if operator not in ("+", "-"):
                return value
            self.position += 1
            right = self.parse_multiplicative()
            value = value + right if operator == "+" else value - right
            value = self.checked(value)

    def parse_multiplicative(self) -> float:
        value = self.parse_unary()
        while True:
            self.skip_whitespace()
            operator = self.peek()
            if operator not in ("*", "/", "%"):
                return value
            self.position += 1
            right = self.parse_unary()
            if operator == "/":
                if right == 0.0:
                    raise CalcError("division by zero")
                value = value / right
            elif operator == "%":
                if right == 0.0:
                    raise CalcError("remainder by zero")
                value = value % right
            else:
                value = value * right
            value = self.checked(value)

    def parse_unary(self) -> float:
        self.skip_whitespace()
        operator = self.peek()
        if operator in ("+", "-"):
            self.position += 1
            value = self.parse_unary()
            if operator == "-":
                value = -value
            return self.checked(value)
        return self.parse_power()

    def parse_power(self) -> float:
        left = self.parse_primary()
        self.skip_whitespace()
        if self.peek() != "^":
            return left
        self.position += 1
        right = self.parse_unary()
        try:
            value = math.pow(left, right)
        except (ValueError, OverflowError) as error:
            raise CalcError("non-finite result") from error
        return self.checked(value)

    def parse_primary(self) -> float:
        self.skip_whitespace()
        if self.peek() == "(":
            self.position += 1
            value = self.parse_additive()
            self.skip_whitespace()
            if self.peek() != ")":
                raise CalcError("expected ')'")
            self.position += 1
            return value
        if self.peek() is not None and (
            "0" <= self.peek() <= "9" or self.peek() == "."
        ):
            return self.parse_number()
        raise CalcError("expected number or '('")

    def parse_number(self) -> float:
        start = self.position
        digits = 0
        while self.peek() is not None and "0" <= self.peek() <= "9":
            self.position += 1
            digits += 1

        if self.peek() == ".":
            self.position += 1
            while self.peek() is not None and "0" <= self.peek() <= "9":
                self.position += 1
                digits += 1

        if digits == 0:
            raise CalcError("expected digits")

        if self.peek() in ("e", "E"):
            self.position += 1
            if self.peek() in ("+", "-"):
                self.position += 1
            exponent_start = self.position
            while self.peek() is not None and "0" <= self.peek() <= "9":
                self.position += 1
            if self.position == exponent_start:
                raise CalcError("expected exponent digits")

        literal = self.text[start : self.position]
        try:
            value = float(literal)
        except (ValueError, OverflowError) as error:
            raise CalcError("invalid number") from error
        return self.checked(value, "non-finite input")


def main() -> int:
    arguments = sys.argv[1:]
    if len(arguments) != 1:
        print("error: expected exactly one expression argument", file=sys.stderr)
        return 1

    try:
        result = Parser(arguments[0]).parse()
    except CalcError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print(repr(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
