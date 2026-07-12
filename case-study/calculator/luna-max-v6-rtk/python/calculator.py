import math
import sys


class ParseError(Exception):
    pass


class Parser:
    def __init__(self, text):
        self.text = text
        self.position = 0

    def fail(self):
        raise ParseError()

    def peek(self):
        if self.position < len(self.text):
            return self.text[self.position]
        return None

    def skip_whitespace(self):
        while self.position < len(self.text) and self.text[self.position] in " \t\n\r\v\f":
            self.position += 1

    @staticmethod
    def checked(value):
        if not math.isfinite(value):
            raise ParseError()
        return value

    def parse(self):
        value = self.parse_additive()
        self.skip_whitespace()
        if self.position != len(self.text):
            self.fail()
        return value

    def parse_additive(self):
        left = self.parse_multiplicative()
        while True:
            self.skip_whitespace()
            operator = self.peek()
            if operator not in ("+", "-"):
                return left
            self.position += 1
            right = self.parse_multiplicative()
            try:
                value = left + right if operator == "+" else left - right
            except (OverflowError, ValueError):
                self.fail()
            left = self.checked(value)

    def parse_multiplicative(self):
        left = self.parse_unary()
        while True:
            self.skip_whitespace()
            operator = self.peek()
            if operator not in ("*", "/", "%"):
                return left
            self.position += 1
            right = self.parse_unary()
            if operator in ("/", "%") and right == 0.0:
                self.fail()
            try:
                if operator == "*":
                    value = left * right
                elif operator == "/":
                    value = left / right
                else:
                    value = math.fmod(left, right)
            except (OverflowError, ValueError, ZeroDivisionError):
                self.fail()
            left = self.checked(value)

    def parse_unary(self):
        self.skip_whitespace()
        operator = self.peek()
        if operator == "+":
            self.position += 1
            return self.parse_unary()
        if operator == "-":
            self.position += 1
            return self.checked(-self.parse_unary())
        return self.parse_power()

    def parse_power(self):
        base = self.parse_primary()
        self.skip_whitespace()
        if self.peek() != "^":
            return base
        self.position += 1
        exponent = self.parse_unary()
        try:
            value = math.pow(base, exponent)
        except (OverflowError, ValueError, ZeroDivisionError):
            self.fail()
        return self.checked(value)

    def parse_primary(self):
        self.skip_whitespace()
        if self.peek() == "(":
            self.position += 1
            value = self.parse_additive()
            self.skip_whitespace()
            if self.peek() != ")":
                self.fail()
            self.position += 1
            return value
        return self.parse_number()

    def parse_number(self):
        self.skip_whitespace()
        start = self.position
        has_digit = False
        while self.peek() is not None and "0" <= self.peek() <= "9":
            self.position += 1
            has_digit = True
        if self.peek() == ".":
            self.position += 1
            while self.peek() is not None and "0" <= self.peek() <= "9":
                self.position += 1
                has_digit = True
        if not has_digit:
            self.fail()
        if self.peek() in ("e", "E"):
            self.position += 1
            if self.peek() in ("+", "-"):
                self.position += 1
            exponent_start = self.position
            while self.peek() is not None and "0" <= self.peek() <= "9":
                self.position += 1
            if self.position == exponent_start:
                self.fail()
        literal = self.text[start:self.position]
        try:
            value = float(literal)
        except (OverflowError, ValueError):
            self.fail()
        if not math.isfinite(value):
            self.fail()
        return value


def main():
    if len(sys.argv) != 2:
        sys.stderr.write("error: invalid expression\n")
        return 1
    try:
        result = Parser(sys.argv[1]).parse()
    except ParseError:
        sys.stderr.write("error: invalid expression\n")
        return 1
    sys.stdout.write(format(result, ".17g") + "\n")
    return 0


raise SystemExit(main())
