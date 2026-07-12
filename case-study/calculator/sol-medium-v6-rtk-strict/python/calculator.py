import math, re, sys

class Parser:
    def __init__(self, s): self.s, self.i = s, 0
    def ws(self):
        while self.i < len(self.s) and self.s[self.i] in ' \t\r\n\f\v': self.i += 1
    def eat(self, c):
        self.ws()
        if self.s.startswith(c, self.i): self.i += len(c); return True
        return False
    def number(self):
        self.ws(); m = re.match(r'(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?', self.s[self.i:])
        if not m: raise ValueError('expected number')
        self.i += len(m.group()); v = float(m.group())
        if not math.isfinite(v): raise ValueError('non-finite value')
        return v
    def primary(self):
        if self.eat('('):
            v = self.add()
            if not self.eat(')'): raise ValueError("expected ')'")
            return v
        return self.number()
    def power(self):
        v = self.primary()
        if self.eat('^'): v = math.pow(v, self.unary())
        return self.check(v)
    def unary(self):
        if self.eat('+'): return self.check(self.unary())
        if self.eat('-'): return self.check(-self.unary())
        return self.power()
    def mul(self):
        v = self.unary()
        while True:
            if self.eat('*'): v *= self.unary()
            elif self.eat('/'):
                r = self.unary()
                if r == 0: raise ValueError('division by zero')
                v /= r
            elif self.eat('%'):
                r = self.unary()
                if r == 0: raise ValueError('remainder by zero')
                v = math.fmod(v, r)
            else: return v
            v = self.check(v)
    def add(self):
        v = self.mul()
        while True:
            if self.eat('+'): v += self.mul()
            elif self.eat('-'): v -= self.mul()
            else: return v
            v = self.check(v)
    def check(self, v):
        if not math.isfinite(v): raise ValueError('non-finite result')
        return v
    def parse(self):
        v = self.add(); self.ws()
        if self.i != len(self.s): raise ValueError('trailing token')
        return v

try:
    if len(sys.argv) != 2: raise ValueError('expected one expression')
    print(format(Parser(sys.argv[1]).parse(), '.17g'))
except (ValueError, OverflowError) as e:
    print('error:', e, file=sys.stderr); sys.exit(1)
