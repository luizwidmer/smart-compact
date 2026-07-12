#!/usr/bin/env python3
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

    def take(self, char):
        self.space()
        if self.pos < len(self.text) and self.text[self.pos] == char:
            self.pos += 1
            return True
        return False

    def parse(self):
        value = self.add()
        self.space()
        if self.pos != len(self.text):
            raise ValueError("unexpected token")
        return value

    def add(self):
        value = self.mul()
        while True:
            if self.take('+'):
                value = checked(value + self.mul())
            elif self.take('-'):
                value = checked(value - self.mul())
            else:
                return value

    def mul(self):
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
                value = checked(math.pow(value, self.unary()))
            except (ValueError, OverflowError):
                raise ValueError("invalid exponentiation")
        return value

    def primary(self):
        if self.take('('):
            value = self.add()
            if not self.take(')'):
                raise ValueError("expected closing parenthesis")
            return value
        self.space()
        match = NUMBER.match(self.text, self.pos)
        if not match:
            raise ValueError("expected number")
        self.pos = match.end()
        return checked(float(match.group()))


def checked(value):
    if not math.isfinite(value):
        raise ValueError("non-finite result")
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
