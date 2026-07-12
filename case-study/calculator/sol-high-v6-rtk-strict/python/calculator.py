import math
import re
import sys


NUMBER = re.compile(r"(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?")


class Parser:
    def __init__(self, text):
        self.text = text
        self.pos = 0

    def space(self):
        while self.pos < len(self.text) and self.text[self.pos] in " \t\n\r\f\v":
            self.pos += 1

    def take(self, token):
        self.space()
        if self.text.startswith(token, self.pos):
            self.pos += len(token)
            return True
        return False

    def expression(self):
        value = self.product()
        while True:
            if self.take("+"):
                value = self.checked(value + self.product())
            elif self.take("-"):
                value = self.checked(value - self.product())
            else:
                return value

    def product(self):
        value = self.unary()
        while True:
            if self.take("*"):
                value = self.checked(value * self.unary())
            elif self.take("/"):
                rhs = self.unary()
                if rhs == 0.0:
                    raise ValueError("division by zero")
                value = self.checked(value / rhs)
            elif self.take("%"):
                rhs = self.unary()
                if rhs == 0.0:
                    raise ValueError("remainder by zero")
                value = self.checked(math.fmod(value, rhs))
            else:
                return value

    def unary(self):
        if self.take("+"):
            return self.unary()
        if self.take("-"):
            return self.checked(-self.unary())
        return self.power()

    def power(self):
        value = self.primary()
        if self.take("^"):
            try:
                value = math.pow(value, self.unary())
            except (ValueError, OverflowError):
                raise ValueError("invalid exponentiation")
            return self.checked(value)
        return value

    def primary(self):
        if self.take("("):
            value = self.expression()
            if not self.take(")"):
                raise ValueError("expected closing parenthesis")
            return value
        self.space()
        match = NUMBER.match(self.text, self.pos)
        if match is None:
            raise ValueError("expected number")
        self.pos = match.end()
        return self.checked(float(match.group()))

    @staticmethod
    def checked(value):
        if not math.isfinite(value):
            raise ValueError("non-finite value")
        return value

    def parse(self):
        value = self.expression()
        self.space()
        if self.pos != len(self.text):
            raise ValueError("trailing input")
        return value


def main():
    if len(sys.argv) != 2:
        raise ValueError("expected exactly one expression")
    print(format(Parser(sys.argv[1]).parse(), ".17g"))


try:
    main()
except Exception as exc:
    print(f"error: {exc}", file=sys.stderr)
    sys.exit(1)
