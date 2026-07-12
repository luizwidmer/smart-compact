import math
import re
import sys

NUMBER = re.compile(r"(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?")

class Parser:
    def __init__(self, text): self.text, self.pos = text, 0
    def space(self):
        while self.pos < len(self.text) and self.text[self.pos] in " \t\n\r\v\f": self.pos += 1
    def take(self, token):
        self.space()
        if self.text.startswith(token, self.pos): self.pos += len(token); return True
        return False
    def expression(self):
        value = self.term()
        while True:
            if self.take('+'): value = checked(value + self.term())
            elif self.take('-'): value = checked(value - self.term())
            else: return value
    def term(self):
        value = self.unary()
        while True:
            if self.take('*'): value = checked(value * self.unary())
            elif self.take('/'):
                rhs = self.unary()
                if rhs == 0: raise ValueError()
                value = checked(value / rhs)
            elif self.take('%'):
                rhs = self.unary()
                if rhs == 0: raise ValueError()
                value = checked(math.fmod(value, rhs))
            else: return value
    def unary(self):
        if self.take('+'): return self.unary()
        if self.take('-'): return checked(-self.unary())
        return self.power()
    def power(self):
        value = self.primary()
        if self.take('^'):
            try: value = math.pow(value, self.unary())
            except (ValueError, OverflowError): raise ValueError()
            value = checked(value)
        return value
    def primary(self):
        if self.take('('):
            value = self.expression()
            if not self.take(')'): raise ValueError()
            return value
        self.space(); match = NUMBER.match(self.text, self.pos)
        if not match: raise ValueError()
        self.pos = match.end(); return checked(float(match.group()))

def checked(value):
    if not math.isfinite(value): raise ValueError()
    return value

try:
    if len(sys.argv) != 2: raise ValueError()
    parser = Parser(sys.argv[1]); result = parser.expression(); parser.space()
    if parser.pos != len(parser.text): raise ValueError()
    print(format(result, '.17g'))
except Exception:
    print('error: invalid expression', file=sys.stderr)
    sys.exit(1)
