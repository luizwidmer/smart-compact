import math
import sys


class CalcError(Exception):
    pass


class Parser:
    def __init__(self, source: str):
        self.source = source
        self.pos = 0

    def skip_space(self):
        while self.pos < len(self.source) and self.source[self.pos] in " \t\n\r\v\f":
            self.pos += 1

    def take(self, token: str) -> bool:
        self.skip_space()
        if self.source.startswith(token, self.pos):
            self.pos += len(token)
            return True
        return False

    def parse(self) -> float:
        value = self.parse_additive()
        self.skip_space()
        if self.pos != len(self.source):
            raise CalcError("trailing tokens")
        return value

    def parse_additive(self) -> float:
        value = self.parse_multiplicative()
        while True:
            if self.take("+"):
                value = self.checked(value + self.parse_multiplicative())
            elif self.take("-"):
                value = self.checked(value - self.parse_multiplicative())
            else:
                return value

    def parse_multiplicative(self) -> float:
        value = self.parse_unary()
        while True:
            if self.take("*"):
                value = self.checked(value * self.parse_unary())
            elif self.take("/"):
                rhs = self.parse_unary()
                if rhs == 0.0:
                    raise CalcError("division by zero")
                value = self.checked(value / rhs)
            elif self.take("%"):
                rhs = self.parse_unary()
                if rhs == 0.0:
                    raise CalcError("remainder by zero")
                value = self.checked(math.fmod(value, rhs))
            else:
                return value

    def parse_unary(self) -> float:
        if self.take("+"):
            return self.parse_unary()
        if self.take("-"):
            return self.checked(-self.parse_unary())
        return self.parse_power()

    def parse_power(self) -> float:
        value = self.parse_primary()
        if self.take("^"):
            try:
                value = math.pow(value, self.parse_unary())
            except (ValueError, OverflowError) as exc:
                raise CalcError("invalid exponentiation") from exc
            value = self.checked(value)
        return value

    def parse_primary(self) -> float:
        self.skip_space()
        if self.take("("):
            value = self.parse_additive()
            if not self.take(")"):
                raise CalcError("missing closing parenthesis")
            return value

        start = self.pos
        digits_before = 0
        while self.pos < len(self.source) and self.source[self.pos].isdigit() and ord(self.source[self.pos]) < 128:
            self.pos += 1
            digits_before += 1
        digits_after = 0
        if self.pos < len(self.source) and self.source[self.pos] == ".":
            self.pos += 1
            while self.pos < len(self.source) and self.source[self.pos].isdigit() and ord(self.source[self.pos]) < 128:
                self.pos += 1
                digits_after += 1
        if digits_before == 0 and digits_after == 0:
            raise CalcError("expected number or parenthesis")
        if self.pos < len(self.source) and self.source[self.pos] in "eE":
            self.pos += 1
            if self.pos < len(self.source) and self.source[self.pos] in "+-":
                self.pos += 1
            exponent_start = self.pos
            while self.pos < len(self.source) and self.source[self.pos].isdigit() and ord(self.source[self.pos]) < 128:
                self.pos += 1
            if self.pos == exponent_start:
                raise CalcError("invalid exponent")

        token = self.source[start:self.pos]
        try:
            value = float(token)
        except ValueError as exc:
            raise CalcError("invalid number") from exc
        return self.checked(value)

    @staticmethod
    def checked(value: float) -> float:
        if not math.isfinite(value):
            raise CalcError("non-finite result")
        return value


def main() -> int:
    if len(sys.argv) != 2:
        print("error: expected exactly one expression", file=sys.stderr)
        return 1
    try:
        result = Parser(sys.argv[1]).parse()
        print(format(result, ".17g"))
        return 0
    except CalcError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
