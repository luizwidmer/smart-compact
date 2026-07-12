#include <cmath>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <locale.h>
#include <stdexcept>
#include <string>

class CalcError : public std::runtime_error {
public:
    explicit CalcError(const std::string& message) : std::runtime_error(message) {}
};

class Parser {
public:
    explicit Parser(const std::string& input) : input_(input) {}

    double parse() {
        double value = parse_additive();
        skip_whitespace();
        if (position_ != input_.size()) {
            throw CalcError("unexpected trailing token");
        }
        return checked(value, "non-finite result");
    }

private:
    const std::string& input_;
    std::size_t position_ = 0;

    static bool is_digit(char character) {
        return character >= '0' && character <= '9';
    }

    static bool is_ascii_whitespace(unsigned char character) {
        return (character >= 9 && character <= 13) || character == 32;
    }

    char peek() const {
        return position_ < input_.size() ? input_[position_] : '\0';
    }

    void skip_whitespace() {
        while (position_ < input_.size() && is_ascii_whitespace(static_cast<unsigned char>(input_[position_]))) {
            ++position_;
        }
    }

    static double checked(double value, const char* message) {
        if (!std::isfinite(value)) {
            throw CalcError(message);
        }
        return value;
    }

    double parse_additive() {
        double value = parse_multiplicative();
        while (true) {
            skip_whitespace();
            const char operator_character = peek();
            if (operator_character != '+' && operator_character != '-') {
                return value;
            }
            ++position_;
            const double right = parse_multiplicative();
            value = operator_character == '+' ? value + right : value - right;
            value = checked(value, "non-finite result");
        }
    }

    double parse_multiplicative() {
        double value = parse_unary();
        while (true) {
            skip_whitespace();
            const char operator_character = peek();
            if (operator_character != '*' && operator_character != '/' && operator_character != '%') {
                return value;
            }
            ++position_;
            const double right = parse_unary();
            if (operator_character == '/') {
                if (right == 0.0) {
                    throw CalcError("division by zero");
                }
                value /= right;
            } else if (operator_character == '%') {
                if (right == 0.0) {
                    throw CalcError("remainder by zero");
                }
                value = std::fmod(value, right);
            } else {
                value *= right;
            }
            value = checked(value, "non-finite result");
        }
    }

    double parse_unary() {
        skip_whitespace();
        const char operator_character = peek();
        if (operator_character == '+' || operator_character == '-') {
            ++position_;
            double value = parse_unary();
            if (operator_character == '-') {
                value = -value;
            }
            return checked(value, "non-finite result");
        }
        return parse_power();
    }

    double parse_power() {
        const double left = parse_primary();
        skip_whitespace();
        if (peek() != '^') {
            return left;
        }
        ++position_;
        const double right = parse_unary();
        return checked(std::pow(left, right), "non-finite result");
    }

    double parse_primary() {
        skip_whitespace();
        if (peek() == '(') {
            ++position_;
            const double value = parse_additive();
            skip_whitespace();
            if (peek() != ')') {
                throw CalcError("expected ')'");
            }
            ++position_;
            return value;
        }
        if (is_digit(peek()) || peek() == '.') {
            return parse_number();
        }
        throw CalcError("expected number or '('");
    }

    double parse_number() {
        const std::size_t start = position_;
        std::size_t digits = 0;
        while (is_digit(peek())) {
            ++position_;
            ++digits;
        }
        if (peek() == '.') {
            ++position_;
            while (is_digit(peek())) {
                ++position_;
                ++digits;
            }
        }
        if (digits == 0) {
            throw CalcError("expected digits");
        }
        if (peek() == 'e' || peek() == 'E') {
            ++position_;
            if (peek() == '+' || peek() == '-') {
                ++position_;
            }
            const std::size_t exponent_start = position_;
            while (is_digit(peek())) {
                ++position_;
            }
            if (position_ == exponent_start) {
                throw CalcError("expected exponent digits");
            }
        }

        const std::string literal = input_.substr(start, position_ - start);
        char* end = nullptr;
        const double value = std::strtod(literal.c_str(), &end);
        if (end != literal.c_str() + literal.size()) {
            throw CalcError("invalid number");
        }
        return checked(value, "non-finite input");
    }
};

int main(int argc, char* argv[]) {
    if (argc != 2) {
        std::cerr << "error: expected exactly one expression argument\n";
        return 1;
    }
    setlocale(LC_NUMERIC, "C");

    try {
        const std::string expression(argv[1]);
        const double result = Parser(expression).parse();
        std::cout << std::setprecision(17) << result << '\n';
        return 0;
    } catch (const CalcError& error) {
        std::cerr << "error: " << error.what() << '\n';
        return 1;
    }
}
