import math
import re
import sys


NUMBER = re.compile(r"(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?")


class ParseError(Exception):
    pass


class Parser:
    def __init__(self, text):
        self.text = text
        self.pos = 0

    def skip_space(self):
        while self.pos < len(self.text) and self.text[self.pos] in " \t\n\r\v\f":
            self.pos += 1

    def take(self, char):
        self.skip_space()
        if self.pos < len(self.text) and self.text[self.pos] == char:
            self.pos += 1
            return True
        return False

    def parse(self):
        value = self.addition()
        self.skip_space()
        if self.pos != len(self.text):
            raise ParseError("trailing token")
        return value

    def addition(self):
        value = self.multiplication()
        while True:
            if self.take('+'):
                value = self.checked(value + self.multiplication())
            elif self.take('-'):
                value = self.checked(value - self.multiplication())
            else:
                return value

    def multiplication(self):
        value = self.unary()
        while True:
            if self.take('*'):
                value = self.checked(value * self.unary())
            elif self.take('/'):
                right = self.unary()
                if right == 0:
                    raise ParseError("division by zero")
                value = self.checked(value / right)
            elif self.take('%'):
                right = self.unary()
                if right == 0:
                    raise ParseError("remainder by zero")
                value = self.checked(math.fmod(value, right))
            else:
                return value

    def unary(self):
        if self.take('+'):
            return self.unary()
        if self.take('-'):
            return self.checked(-self.unary())
        return self.power()

    def power(self):
        value = self.primary()
        if self.take('^'):
            value = self.checked(math.pow(value, self.unary()))
        return value

    def primary(self):
        if self.take('('):
            value = self.addition()
            if not self.take(')'):
                raise ParseError("missing closing parenthesis")
            return value
        self.skip_space()
        match = NUMBER.match(self.text, self.pos)
        if not match:
            raise ParseError("expected number or parenthesis")
        self.pos = match.end()
        value = float(match.group(0))
        return self.checked(value)

    @staticmethod
    def checked(value):
        if not math.isfinite(value):
            raise ParseError("non-finite result")
        return value


def main():
    if len(sys.argv) != 2:
        print("error: expected exactly one expression", file=sys.stderr)
        return 2
    try:
        result = Parser(sys.argv[1]).parse()
        print(format(result, ".17g"))
        return 0
    except (ParseError, ValueError, OverflowError, ZeroDivisionError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


sys.exit(main())
