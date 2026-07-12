#!/usr/bin/env python3
import math
import sys


class CalcError(Exception):
    pass


class Parser:
    def __init__(self, text):
        self.text = text
        self.pos = 0

    def whitespace(self):
        while self.pos < len(self.text) and self.text[self.pos] in " \t\n\r\v\f":
            self.pos += 1

    def number(self):
        self.whitespace()
        start = self.pos
        digits_before = 0
        while self.pos < len(self.text) and self.text[self.pos].isdigit() and ord(self.text[self.pos]) < 128:
            self.pos += 1
            digits_before += 1
        digits_after = 0
        if self.pos < len(self.text) and self.text[self.pos] == ".":
            self.pos += 1
            while self.pos < len(self.text) and self.text[self.pos].isdigit() and ord(self.text[self.pos]) < 128:
                self.pos += 1
                digits_after += 1
        if digits_before + digits_after == 0:
            self.pos = start
            raise CalcError("expected number")
        if self.pos < len(self.text) and self.text[self.pos] in "eE":
            self.pos += 1
            if self.pos < len(self.text) and self.text[self.pos] in "+-":
                self.pos += 1
            exponent_start = self.pos
            while self.pos < len(self.text) and self.text[self.pos].isdigit() and ord(self.text[self.pos]) < 128:
                self.pos += 1
            if self.pos == exponent_start:
                raise CalcError("malformed exponent")
        try:
            value = float(self.text[start:self.pos])
        except ValueError as exc:
            raise CalcError("invalid number") from exc
        if not math.isfinite(value):
            raise CalcError("non-finite number")
        return value

    def primary(self):
        self.whitespace()
        if self.pos < len(self.text) and self.text[self.pos] == "(":
            self.pos += 1
            value = self.additive()
            self.whitespace()
            if self.pos >= len(self.text) or self.text[self.pos] != ")":
                raise CalcError("expected closing parenthesis")
            self.pos += 1
            return value
        return self.number()

    def power(self):
        left = self.primary()
        self.whitespace()
        if self.pos < len(self.text) and self.text[self.pos] == "^":
            self.pos += 1
            right = self.unary()
            try:
                left = math.pow(left, right)
            except (ValueError, OverflowError) as exc:
                raise CalcError("invalid power") from exc
            if not math.isfinite(left):
                raise CalcError("non-finite result")
        return left

    def unary(self):
        self.whitespace()
        if self.pos < len(self.text) and self.text[self.pos] in "+-":
            sign = self.text[self.pos]
            self.pos += 1
            value = self.unary()
            return -value if sign == "-" else value
        return self.power()

    def multiplicative(self):
        value = self.unary()
        while True:
            self.whitespace()
            if self.pos >= len(self.text) or self.text[self.pos] not in "*/%":
                return value
            operator = self.text[self.pos]
            self.pos += 1
            right = self.unary()
            if right == 0.0:
                raise CalcError("division by zero")
            if operator == "*":
                value *= right
            elif operator == "/":
                value /= right
            else:
                value = math.fmod(value, right)
            if not math.isfinite(value):
                raise CalcError("non-finite result")

    def additive(self):
        value = self.multiplicative()
        while True:
            self.whitespace()
            if self.pos >= len(self.text) or self.text[self.pos] not in "+-":
                return value
            operator = self.text[self.pos]
            self.pos += 1
            right = self.multiplicative()
            value = value + right if operator == "+" else value - right
            if not math.isfinite(value):
                raise CalcError("non-finite result")

    def parse(self):
        self.whitespace()
        if self.pos == len(self.text):
            raise CalcError("empty expression")
        value = self.additive()
        self.whitespace()
        if self.pos != len(self.text):
            raise CalcError("trailing tokens")
        return value


def main():
    try:
        if len(sys.argv) != 2:
            raise CalcError("expected exactly one expression")
        value = Parser(sys.argv[1]).parse()
        print(repr(value))
    except CalcError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


sys.exit(main())
