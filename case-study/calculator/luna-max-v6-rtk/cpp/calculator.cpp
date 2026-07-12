#include <cmath>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <string>

struct ParseError {};

class Parser {
public:
    explicit Parser(const std::string& input) : input_(input) {}

    double parse() {
        const double value = parse_additive();
        skip_whitespace();
        if (position_ != input_.size()) {
            fail();
        }
        return value;
    }

private:
    const std::string& input_;
    std::size_t position_ = 0;

    [[noreturn]] static void fail() {
        throw ParseError{};
    }

    static bool is_digit(char character) {
        return character >= '0' && character <= '9';
    }

    static bool is_whitespace(char character) {
        switch (static_cast<unsigned char>(character)) {
            case ' ':
            case '\t':
            case '\n':
            case '\r':
            case '\v':
            case '\f':
                return true;
            default:
                return false;
        }
    }

    char peek() const {
        return position_ < input_.size() ? input_[position_] : '\0';
    }

    void skip_whitespace() {
        while (position_ < input_.size() && is_whitespace(input_[position_])) {
            ++position_;
        }
    }

    static double checked(double value) {
        if (!std::isfinite(value)) {
            fail();
        }
        return value;
    }

    double parse_additive() {
        double left = parse_multiplicative();
        while (true) {
            skip_whitespace();
            const char operator_character = peek();
            if (operator_character != '+' && operator_character != '-') {
                return left;
            }
            ++position_;
            const double right = parse_multiplicative();
            const double value = operator_character == '+' ? left + right : left - right;
            left = checked(value);
        }
    }

    double parse_multiplicative() {
        double left = parse_unary();
        while (true) {
            skip_whitespace();
            const char operator_character = peek();
            if (operator_character != '*' && operator_character != '/' && operator_character != '%') {
                return left;
            }
            ++position_;
            const double right = parse_unary();
            if ((operator_character == '/' || operator_character == '%') && right == 0.0) {
                fail();
            }
            double value;
            if (operator_character == '*') {
                value = left * right;
            } else if (operator_character == '/') {
                value = left / right;
            } else {
                value = std::fmod(left, right);
            }
            left = checked(value);
        }
    }

    double parse_unary() {
        skip_whitespace();
        if (peek() == '+') {
            ++position_;
            return parse_unary();
        }
        if (peek() == '-') {
            ++position_;
            return checked(-parse_unary());
        }
        return parse_power();
    }

    double parse_power() {
        const double base = parse_primary();
        skip_whitespace();
        if (peek() != '^') {
            return base;
        }
        ++position_;
        const double exponent = parse_unary();
        return checked(std::pow(base, exponent));
    }

    double parse_primary() {
        skip_whitespace();
        if (peek() == '(') {
            ++position_;
            const double value = parse_additive();
            skip_whitespace();
            if (peek() != ')') {
                fail();
            }
            ++position_;
            return value;
        }
        return parse_number();
    }

    double parse_number() {
        skip_whitespace();
        const std::size_t start = position_;
        bool has_digit = false;
        while (is_digit(peek())) {
            ++position_;
            has_digit = true;
        }
        if (peek() == '.') {
            ++position_;
            while (is_digit(peek())) {
                ++position_;
                has_digit = true;
            }
        }
        if (!has_digit) {
            fail();
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
                fail();
            }
        }
        const std::string literal = input_.substr(start, position_ - start);
        try {
            std::size_t consumed = 0;
            const double value = std::stod(literal, &consumed);
            if (consumed != literal.size()) {
                fail();
            }
            return checked(value);
        } catch (const ParseError&) {
            throw;
        } catch (...) {
            fail();
        }
    }
};

int main(int argc, char** argv) {
    if (argc != 2) {
        std::cerr << "error: invalid expression\n";
        return 1;
    }
    try {
        const double result = Parser(argv[1]).parse();
        std::cout << std::setprecision(17) << result << '\n';
        return 0;
    } catch (...) {
        std::cerr << "error: invalid expression\n";
        return 1;
    }
}
