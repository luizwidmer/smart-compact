#!/usr/bin/env python3
import math
import re
import sys


NUMBER = re.compile(r"(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?")
WHITESPACE = " \t\n\r\v\f"


class Parser:
    def __init__(self, text):
        self.text = text
        self.pos = 0

    def error(self, message):
        raise ValueError(message)

    def skip_whitespace(self):
        while self.pos < len(self.text) and self.text[self.pos] in WHITESPACE:
            self.pos += 1

    def match(self, token):
        self.skip_whitespace()
        if self.text.startswith(token, self.pos):
            self.pos += len(token)
            return True
        return False

    def parse_number(self):
        self.skip_whitespace()
        match = NUMBER.match(self.text, self.pos)
        if not match:
            self.error("expected number")
        self.pos = match.end()
        value = float(match.group())
        if not math.isfinite(value):
            self.error("non-finite number")
        return value

    def parse_primary(self):
        if self.match("("):
            value = self.parse_expression()
            if not self.match(")"):
                self.error("expected ')' ")
            return value
        return self.parse_number()

    def parse_power(self):
        value = self.parse_primary()
        if self.match("^"):
            exponent = self.parse_unary()
            value = math.pow(value, exponent)
            if not math.isfinite(value):
                self.error("non-finite result")
        return value

    def parse_unary(self):
        if self.match("+"):
            return self.parse_unary()
        if self.match("-"):
            value = -self.parse_unary()
            if not math.isfinite(value):
                self.error("non-finite result")
            return value
        return self.parse_power()

    def parse_multiplicative(self):
        value = self.parse_unary()
        while True:
            if self.match("*"):
                value *= self.parse_unary()
            elif self.match("/"):
                divisor = self.parse_unary()
                if divisor == 0.0:
                    self.error("division by zero")
                value /= divisor
            elif self.match("%"):
                divisor = self.parse_unary()
                if divisor == 0.0:
                    self.error("remainder by zero")
                value %= divisor
            else:
                break
            if not math.isfinite(value):
                self.error("non-finite result")
        return value

    def parse_expression(self):
        value = self.parse_multiplicative()
        while True:
            if self.match("+"):
                value += self.parse_multiplicative()
            elif self.match("-"):
                value -= self.parse_multiplicative()
            else:
                break
            if not math.isfinite(value):
                self.error("non-finite result")
        return value

    def parse(self):
        value = self.parse_expression()
        self.skip_whitespace()
        if self.pos != len(self.text):
            self.error("trailing tokens")
        return value


def main():
    if len(sys.argv) != 2:
        print("error: expected exactly one expression argument", file=sys.stderr)
        return 1
    try:
        print(Parser(sys.argv[1]).parse())
        return 0
    except (ValueError, OverflowError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
