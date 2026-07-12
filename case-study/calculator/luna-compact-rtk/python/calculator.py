import math
import sys


class CalculatorError(Exception):
    pass


class Parser:
    def __init__(self, expression):
        self.expression = expression
        self.position = 0

    def parse(self):
        value = self.parse_addition()
        self.skip_whitespace()
        if self.position != len(self.expression):
            raise CalculatorError("unexpected trailing token")
        return value

    def parse_addition(self):
        value = self.parse_multiplication()
        while True:
            if self.consume("+"):
                right = self.parse_multiplication()
                value = self.checked(value + right)
            elif self.consume("-"):
                right = self.parse_multiplication()
                value = self.checked(value - right)
            else:
                return value

    def parse_multiplication(self):
        value = self.parse_unary()
        while True:
            if self.consume("*"):
                right = self.parse_unary()
                value = self.checked(value * right)
            elif self.consume("/"):
                right = self.parse_unary()
                if right == 0.0:
                    raise CalculatorError("division by zero")
                value = self.checked(value / right)
            elif self.consume("%"):
                right = self.parse_unary()
                if right == 0.0:
                    raise CalculatorError("remainder by zero")
                value = self.checked(value % right)
            else:
                return value

    def parse_unary(self):
        if self.consume("+"):
            return self.parse_unary()
        if self.consume("-"):
            return -self.parse_unary()
        return self.parse_power()

    def parse_power(self):
        value = self.parse_primary()
        if self.consume("^"):
            exponent = self.parse_unary()
            try:
                value = math.pow(value, exponent)
            except (ValueError, OverflowError):
                raise CalculatorError("non-finite result")
            return self.checked(value)
        return value

    def parse_primary(self):
        self.skip_whitespace()
        if self.position >= len(self.expression):
            raise CalculatorError("expected a number or parenthesized expression")

        if self.expression[self.position] == "(":
            self.position += 1
            value = self.parse_addition()
            if not self.consume(")"):
                raise CalculatorError("missing closing parenthesis")
            return value

        character = self.expression[self.position]
        if self.is_digit(character) or character == ".":
            return self.parse_number()
        raise CalculatorError("expected a number or parenthesized expression")

    def parse_number(self):
        start = self.position
        digits_before_decimal = 0
        while self.position < len(self.expression) and self.is_digit(
            self.expression[self.position]
        ):
            self.position += 1
            digits_before_decimal += 1

        digits_after_decimal = 0
        if self.position < len(self.expression) and self.expression[self.position] == ".":
            self.position += 1
            while self.position < len(self.expression) and self.is_digit(
                self.expression[self.position]
            ):
                self.position += 1
                digits_after_decimal += 1

        if digits_before_decimal == 0 and digits_after_decimal == 0:
            raise CalculatorError("invalid number")

        if self.position < len(self.expression) and self.expression[self.position] in "eE":
            self.position += 1
            if self.position < len(self.expression) and self.expression[self.position] in "+-":
                self.position += 1
            exponent_digits = 0
            while self.position < len(self.expression) and self.is_digit(
                self.expression[self.position]
            ):
                self.position += 1
                exponent_digits += 1
            if exponent_digits == 0:
                raise CalculatorError("invalid exponent")

        literal = self.expression[start : self.position]
        try:
            value = float(literal)
        except ValueError:
            raise CalculatorError("invalid number")
        return self.checked(value)

    def consume(self, token):
        self.skip_whitespace()
        if self.expression.startswith(token, self.position):
            self.position += len(token)
            return True
        return False

    def skip_whitespace(self):
        while self.position < len(self.expression) and self.is_whitespace(
            self.expression[self.position]
        ):
            self.position += 1

    @staticmethod
    def is_digit(character):
        return "0" <= character <= "9"

    @staticmethod
    def is_whitespace(character):
        return character in " \t\n\r\v\f"

    @staticmethod
    def checked(value):
        if not math.isfinite(value):
            raise CalculatorError("non-finite result")
        return value


def main():
    if len(sys.argv) != 2:
        print("error: expected exactly one expression argument", file=sys.stderr)
        return 1

    try:
        result = Parser(sys.argv[1]).parse()
    except CalculatorError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    except Exception:
        print("error: invalid expression", file=sys.stderr)
        return 1

    print(repr(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
