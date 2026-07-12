import math
import sys


class ParseError(Exception):
    pass


class Parser:
    def __init__(self, text: str):
        self.text = text
        self.length = len(text)
        self.i = 0

    def parse(self) -> float:
        self.skip_ws()
        if self.i >= self.length:
            raise ParseError("empty expression")
        value = self.parse_add_sub()
        self.skip_ws()
        if self.i != self.length:
            raise ParseError("unexpected token")
        if not math.isfinite(value):
            raise ParseError("non-finite result")
        return value

    def parse_add_sub(self) -> float:
        value = self.parse_mul_div()
        while True:
            self.skip_ws()
            if self.match("+"):
                value += self.parse_mul_div()
            elif self.match("-"):
                value -= self.parse_mul_div()
            else:
                break
        return value

    def parse_mul_div(self) -> float:
        value = self.parse_unary()
        while True:
            self.skip_ws()
            if self.match("*"):
                value *= self.parse_unary()
            elif self.match("/"):
                rhs = self.parse_unary()
                if rhs == 0.0:
                    raise ParseError("division by zero")
                value /= rhs
            elif self.match("%"):
                rhs = self.parse_unary()
                if rhs == 0.0:
                    raise ParseError("remainder by zero")
                value %= rhs
            else:
                break
        return value

    def parse_unary(self) -> float:
        self.skip_ws()
        if self.match("+"):
            return self.parse_unary()
        if self.match("-"):
            return -self.parse_unary()
        return self.parse_pow()

    def parse_pow(self) -> float:
        value = self.parse_primary()
        self.skip_ws()
        if self.match("^"):
            right = self.parse_pow()
            value = value ** right
        return value

    def parse_primary(self) -> float:
        self.skip_ws()
        if self.match("("):
            value = self.parse_add_sub()
            self.skip_ws()
            if not self.match(")"):
                raise ParseError("missing closing parenthesis")
            return value
        return self.parse_number()

    def parse_number(self) -> float:
        start = self.i

        has_digit_before = False
        if self.peek() == ".":
            self.i += 1
            if not self.at_end() and self.peek().isdigit():
                while not self.at_end() and self.peek().isdigit():
                    self.i += 1
            else:
                raise ParseError("malformed number")
        else:
            while not self.at_end() and self.peek().isdigit():
                self.i += 1
                has_digit_before = True
            if self.peek() == ".":
                self.i += 1
                while not self.at_end() and self.peek().isdigit():
                    self.i += 1
                if not has_digit_before and self.i - start == 1:
                    raise ParseError("malformed number")
            elif not has_digit_before:
                raise ParseError("malformed number")

        if self.peek().lower() in ("e",):
            self.i += 1
            if not self.at_end() and self.peek() in "+-":
                self.i += 1
            if self.at_end() or not self.peek().isdigit():
                raise ParseError("malformed number")
            while not self.at_end() and self.peek().isdigit():
                self.i += 1

        token = self.text[start:self.i]
        try:
            value = float(token)
        except ValueError:
            raise ParseError("malformed number")

        if not math.isfinite(value):
            raise ParseError("non-finite number")
        return value

    def match(self, ch: str) -> bool:
        if self.i < self.length and self.text[self.i] == ch:
            self.i += 1
            return True
        return False

    def skip_ws(self) -> None:
        while not self.at_end() and self.text[self.i].isspace():
            self.i += 1

    def peek(self) -> str:
        return "" if self.i >= self.length else self.text[self.i]

    def at_end(self) -> bool:
        return self.i >= self.length


def main() -> int:
    if len(sys.argv) != 2:
        print("error: expected one expression argument", file=sys.stderr)
        return 1
    try:
        parser = Parser(sys.argv[1])
        value = parser.parse()
        if value.is_integer():
            if value == 0.0:
                print("0")
            else:
                print(f"{int(value):.0f}")
        else:
            print(repr(value))
    except (ParseError, ZeroDivisionError, OverflowError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
