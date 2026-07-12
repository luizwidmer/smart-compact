import math
import sys


class Parser:
    def __init__(self, text):
        self.text = text
        self.pos = 0

    def skip(self):
        while self.pos < len(self.text) and self.text[self.pos] in " \t\n\r\v\f":
            self.pos += 1

    def take(self, char):
        self.skip()
        if self.pos < len(self.text) and self.text[self.pos] == char:
            self.pos += 1
            return True
        return False

    def parse(self):
        value = self.expression()
        self.skip()
        if self.pos != len(self.text):
            raise ValueError("unexpected token")
        return value

    def expression(self):
        value = self.term()
        while True:
            if self.take("+"):
                value = checked(value + self.term())
            elif self.take("-"):
                value = checked(value - self.term())
            else:
                return value

    def term(self):
        value = self.unary()
        while True:
            if self.take("*"):
                value = checked(value * self.unary())
            elif self.take("/"):
                rhs = self.unary()
                if rhs == 0:
                    raise ValueError("division by zero")
                value = checked(value / rhs)
            elif self.take("%"):
                rhs = self.unary()
                if rhs == 0:
                    raise ValueError("remainder by zero")
                value = checked(math.fmod(value, rhs))
            else:
                return value

    def unary(self):
        if self.take("+"):
            return self.unary()
        if self.take("-"):
            return checked(-self.unary())
        return self.power()

    def power(self):
        value = self.primary()
        if self.take("^"):
            try:
                value = math.pow(value, self.unary())
            except (OverflowError, ValueError):
                raise ValueError("non-finite result")
            return checked(value)
        return value

    def primary(self):
        if self.take("("):
            value = self.expression()
            if not self.take(")"):
                raise ValueError("expected ')'")
            return value
        return self.number()

    def number(self):
        self.skip()
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
        if before + after == 0:
            raise ValueError("expected number")
        if self.pos < len(self.text) and self.text[self.pos] in "eE":
            self.pos += 1
            if self.pos < len(self.text) and self.text[self.pos] in "+-":
                self.pos += 1
            exponent = self.pos
            while self.pos < len(self.text) and self.text[self.pos].isdigit() and self.text[self.pos].isascii():
                self.pos += 1
            if self.pos == exponent:
                raise ValueError("malformed exponent")
        return checked(float(self.text[start:self.pos]))


def checked(value):
    if not math.isfinite(value):
        raise ValueError("non-finite value")
    return value


try:
    if len(sys.argv) != 2:
        raise ValueError("expected exactly one expression")
    print(repr(Parser(sys.argv[1]).parse()))
except Exception as error:
    print(f"error: {error}", file=sys.stderr)
    sys.exit(1)
