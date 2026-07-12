#!/usr/bin/env python3
import math
import re
import sys

NUMBER = re.compile(r"(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?")


class Parser:
    def __init__(self, text):
        self.text = text
        self.pos = 0

    def skip(self):
        while self.pos < len(self.text) and self.text[self.pos] in " \t\r\n\v\f":
            self.pos += 1

    def take(self, char):
        self.skip()
        if self.pos < len(self.text) and self.text[self.pos] == char:
            self.pos += 1
            return True
        return False

    def parse(self):
        value = self.additive()
        self.skip()
        if self.pos != len(self.text):
            raise ValueError("unexpected token")
        return checked(value)

    def additive(self):
        value = self.multiplicative()
        while True:
            if self.take('+'):
                value = checked(value + self.multiplicative())
            elif self.take('-'):
                value = checked(value - self.multiplicative())
            else:
                return value

    def multiplicative(self):
        value = self.unary()
        while True:
            if self.take('*'):
                value = checked(value * self.unary())
            elif self.take('/'):
                rhs = self.unary()
                if rhs == 0.0:
                    raise ValueError("division by zero")
                value = checked(value / rhs)
            elif self.take('%'):
                rhs = self.unary()
                if rhs == 0.0:
                    raise ValueError("remainder by zero")
                value = checked(math.fmod(value, rhs))
            else:
                return value

    def unary(self):
        if self.take('+'):
            return self.unary()
        if self.take('-'):
            return checked(-self.unary())
        return self.power()

    def power(self):
        value = self.primary()
        if self.take('^'):
            try:
                value = math.pow(value, self.unary())
            except (ValueError, OverflowError):
                raise ValueError("non-finite result")
        return checked(value)

    def primary(self):
        if self.take('('):
            value = self.additive()
            if not self.take(')'):
                raise ValueError("expected closing parenthesis")
            return value
        self.skip()
        match = NUMBER.match(self.text, self.pos)
        if not match:
            raise ValueError("expected number")
        self.pos = match.end()
        return checked(float(match.group()))


def checked(value):
    if not math.isfinite(value):
        raise ValueError("non-finite value")
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
