import math
import sys


class Parser:
    def __init__(self, expr: str):
        self.s = expr
        self.i = 0
        self.n = len(expr)

    def parse(self) -> float:
        value = self.parse_expr()
        self.skip_ws()
        if self.i != self.n:
            self.error("trailing tokens")
        if not math.isfinite(value):
            self.error("non-finite result")
        return value

    def parse_expr(self) -> float:
        value = self.parse_add()
        return value

    def parse_add(self) -> float:
        value = self.parse_mul()
        while True:
            self.skip_ws()
            if self.match('+'):
                rhs = self.parse_mul()
                value += rhs
            elif self.match('-'):
                rhs = self.parse_mul()
                value -= rhs
            else:
                break
            self.ensure_finite(value)
        return value

    def parse_mul(self) -> float:
        value = self.parse_unary()
        while True:
            self.skip_ws()
            if self.match('*'):
                rhs = self.parse_unary()
                value *= rhs
            elif self.match('/'):
                rhs = self.parse_unary()
                if rhs == 0.0:
                    self.error("division by zero")
                value /= rhs
            elif self.match('%'):
                rhs = self.parse_unary()
                if rhs == 0.0:
                    self.error("remainder by zero")
                value %= rhs
            else:
                break
            self.ensure_finite(value)
        return value

    def parse_unary(self) -> float:
        self.skip_ws()
        if self.match('+'):
            return self.parse_unary()
        if self.match('-'):
            return -self.parse_unary()
        return self.parse_pow()

    def parse_pow(self) -> float:
        value = self.parse_primary()
        self.skip_ws()
        if self.match('^'):
            rhs = self.parse_pow()
            value = math.pow(value, rhs)
        self.ensure_finite(value)
        return value

    def parse_primary(self) -> float:
        self.skip_ws()
        if self.match('('):
            value = self.parse_expr()
            self.skip_ws()
            if not self.match(')'):
                self.error("missing closing parenthesis")
            self.skip_ws()
            return value
        return self.parse_number()

    def parse_number(self) -> float:
        self.skip_ws()
        start = self.i

        saw_digit = False
        saw_dot = False

        while self.i < self.n and self.s[self.i].isdigit():
            self.i += 1
            saw_digit = True

        if self.i < self.n and self.s[self.i] == '.':
            saw_dot = True
            self.i += 1
            while self.i < self.n and self.s[self.i].isdigit():
                self.i += 1
                saw_digit = True

        if not saw_digit and not saw_dot:
            self.error("expected number")

        if self.i < self.n and self.s[self.i] in 'eE':
            self.i += 1
            if self.i < self.n and self.s[self.i] in '+-':
                self.i += 1
            if self.i >= self.n or not self.s[self.i].isdigit():
                self.error("invalid exponent")
            while self.i < self.n and self.s[self.i].isdigit():
                self.i += 1

        token = self.s[start:self.i]
        try:
            value = float(token)
        except ValueError:
            self.error("invalid number")

        if not math.isfinite(value):
            self.error("non-finite literal")
        return value

    def skip_ws(self) -> None:
        while self.i < self.n and self.s[self.i].isspace():
            self.i += 1

    def match(self, ch: str) -> bool:
        if self.i < self.n and self.s[self.i] == ch:
            self.i += 1
            return True
        return False

    def ensure_finite(self, value: float) -> None:
        if not math.isfinite(value):
            self.error("non-finite result")

    def error(self, msg: str) -> None:
        raise ValueError(msg)


def main() -> int:
    if len(sys.argv) != 2:
        print("error: expected exactly one expression argument", file=sys.stderr)
        return 1

    parser = Parser(sys.argv[1])
    try:
        result = parser.parse()
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if result == -0.0:
        result = 0.0
    print(format(result, ".17g"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
