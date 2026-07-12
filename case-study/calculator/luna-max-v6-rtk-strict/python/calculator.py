import math
import sys


class ParseError(Exception):
    pass


class Parser:
    def __init__(self, text):
        self.text = text
        self.position = 0

    def parse(self):
        value = self.parse_additive()
        self.skip_whitespace()
        if self.position != len(self.text):
            raise ParseError("trailing tokens")
        return self.checked(value)

    def skip_whitespace(self):
        while self.position < len(self.text) and self.text[self.position] in " \t\n\r\f\v":
            self.position += 1

    def peek(self):
        self.skip_whitespace()
        if self.position == len(self.text):
            return None
        return self.text[self.position]

    @staticmethod
    def checked(value):
        if not math.isfinite(value):
            raise ParseError("non-finite result")
        return value

    def parse_additive(self):
        left = self.parse_multiplicative()
        while True:
            operator = self.peek()
            if operator not in ("+", "-"):
                return left
            self.position += 1
            right = self.parse_multiplicative()
            left = self.checked(left + right if operator == "+" else left - right)

    def parse_multiplicative(self):
        left = self.parse_unary()
        while True:
            operator = self.peek()
            if operator not in ("*", "/", "%"):
                return left
            self.position += 1
            right = self.parse_unary()
            if operator in ("/", "%") and right == 0.0:
                raise ParseError("division or remainder by zero")
            if operator == "*":
                result = left * right
            elif operator == "/":
                result = left / right
            else:
                result = math.fmod(left, right)
            left = self.checked(result)

    def parse_unary(self):
        operator = self.peek()
        if operator in ("+", "-"):
            self.position += 1
            value = self.parse_unary()
            return self.checked(value if operator == "+" else -value)
        return self.parse_power()

    def parse_power(self):
        base = self.parse_primary()
        if self.peek() == "^":
            self.position += 1
            exponent = self.parse_unary()
            try:
                result = math.pow(base, exponent)
            except (ValueError, OverflowError) as error:
                raise ParseError("invalid exponentiation") from error
            return self.checked(result)
        return base

    def parse_primary(self):
        if self.peek() == "(":
            self.position += 1
            value = self.parse_additive()
            if self.peek() != ")":
                raise ParseError("missing closing parenthesis")
            self.position += 1
            return value
        return self.parse_number()

    def parse_number(self):
        self.skip_whitespace()
        start = self.position
        digits_before = 0
        while self.position < len(self.text) and self.text[self.position].isdigit() and self.text[self.position].isascii():
            self.position += 1
            digits_before += 1

        digits_after = 0
        if self.position < len(self.text) and self.text[self.position] == ".":
            self.position += 1
            while self.position < len(self.text) and self.text[self.position].isdigit() and self.text[self.position].isascii():
                self.position += 1
                digits_after += 1

        if digits_before == 0 and digits_after == 0:
            raise ParseError("expected number or parenthesis")

        if self.position < len(self.text) and self.text[self.position] in "eE":
            self.position += 1
            if self.position < len(self.text) and self.text[self.position] in "+-":
                self.position += 1
            exponent_start = self.position
            while self.position < len(self.text) and self.text[self.position].isdigit() and self.text[self.position].isascii():
                self.position += 1
            if self.position == exponent_start:
                raise ParseError("malformed exponent")

        token = self.text[start:self.position]
        try:
            value = float(token)
        except ValueError as error:
            raise ParseError("invalid number") from error
        return self.checked(value)


def main():
    if len(sys.argv) != 2:
        raise ParseError("expected exactly one expression argument")
    result = Parser(sys.argv[1]).parse()
    sys.stdout.write(format(result, ".17g") + "\n")


try:
    main()
except Exception as error:
    sys.stderr.write(f"error: {error}\n")
    sys.exit(1)
