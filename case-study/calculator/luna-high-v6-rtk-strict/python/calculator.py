import math
import sys


class ParseError(Exception):
    pass


class Parser:
    def __init__(self, text):
        self.text = text
        self.pos = 0

    @staticmethod
    def is_space(char):
        return char in " \t\n\r\v\f"

    def skip_space(self):
        while self.pos < len(self.text) and self.is_space(self.text[self.pos]):
            self.pos += 1

    @staticmethod
    def checked(value):
        if not math.isfinite(value):
            raise ParseError("non-finite result")
        return value

    def parse(self):
        value = self.parse_additive()
        self.skip_space()
        if self.pos != len(self.text):
            raise ParseError("trailing tokens")
        return self.checked(value)

    def parse_additive(self):
        value = self.parse_multiplicative()
        while True:
            self.skip_space()
            if self.pos >= len(self.text) or self.text[self.pos] not in "+-":
                return value
            operator = self.text[self.pos]
            self.pos += 1
            right = self.parse_multiplicative()
            value = self.checked(value + right if operator == "+" else value - right)

    def parse_multiplicative(self):
        value = self.parse_unary()
        while True:
            self.skip_space()
            if self.pos >= len(self.text) or self.text[self.pos] not in "*/%":
                return value
            operator = self.text[self.pos]
            self.pos += 1
            right = self.parse_unary()
            if right == 0.0:
                raise ParseError("division by zero")
            if operator == "*":
                value = self.checked(value * right)
            elif operator == "/":
                value = self.checked(value / right)
            else:
                value = self.checked(value % right)

    def parse_unary(self):
        self.skip_space()
        if self.pos < len(self.text) and self.text[self.pos] in "+-":
            operator = self.text[self.pos]
            self.pos += 1
            value = self.parse_unary()
            return self.checked(value if operator == "+" else -value)
        return self.parse_power()

    def parse_power(self):
        value = self.parse_primary()
        self.skip_space()
        if self.pos < len(self.text) and self.text[self.pos] == "^":
            self.pos += 1
            value = self.checked(math.pow(value, self.parse_unary()))
        return value

    def parse_primary(self):
        self.skip_space()
        if self.pos >= len(self.text):
            raise ParseError("expected expression")
        if self.text[self.pos] == "(":
            self.pos += 1
            value = self.parse_additive()
            self.skip_space()
            if self.pos >= len(self.text) or self.text[self.pos] != ")":
                raise ParseError("expected closing parenthesis")
            self.pos += 1
            return value
        return self.parse_number()

    def parse_number(self):
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
            raise ParseError("expected number")
        if self.pos < len(self.text) and self.text[self.pos] in "eE":
            self.pos += 1
            if self.pos < len(self.text) and self.text[self.pos] in "+-":
                self.pos += 1
            exponent_start = self.pos
            while self.pos < len(self.text) and self.text[self.pos].isdigit() and self.text[self.pos].isascii():
                self.pos += 1
            if self.pos == exponent_start:
                raise ParseError("invalid exponent")
        try:
            return self.checked(float(self.text[start:self.pos]))
        except ValueError as error:
            raise ParseError("invalid number") from error


def main():
    if len(sys.argv) != 2:
        raise ParseError("expected exactly one argument")
    result = Parser(sys.argv[1]).parse()
    print(format(result, ".17g"))


try:
    main()
except Exception as error:
    print(f"error: {error}", file=sys.stderr)
    sys.exit(1)
