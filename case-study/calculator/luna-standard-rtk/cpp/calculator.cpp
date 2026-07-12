#include <cmath>
#include <exception>
#include <iomanip>
#include <iostream>
#include <limits>
#include <locale>
#include <stdexcept>
#include <string>

class Parser {
public:
    explicit Parser(const std::string& expression) : input(expression), position(0) {}

    double parse() {
        double result = parse_add_sub();
        skip_whitespace();
        if (position != input.size()) {
            fail("trailing tokens");
        }
        return checked(result);
    }

private:
    const std::string& input;
    std::size_t position;

    static bool is_digit(char character) {
        return character >= '0' && character <= '9';
    }

    static bool is_whitespace(char character) {
        return character == ' ' || character == '\t' || character == '\r' ||
               character == '\n' || character == '\v' || character == '\f';
    }

    bool at_end() const {
        return position == input.size();
    }

    char current() const {
        return at_end() ? '\0' : input[position];
    }

    void skip_whitespace() {
        while (!at_end() && is_whitespace(current())) {
            ++position;
        }
    }

    static double checked(double value) {
        if (!std::isfinite(value)) {
            throw std::runtime_error("non-finite result");
        }
        return value;
    }

    [[noreturn]] static void fail(const char* message) {
        throw std::runtime_error(message);
    }

    double parse_add_sub() {
        double value = parse_mul_div();
        while (true) {
            skip_whitespace();
            char operator_character = current();
            if (operator_character != '+' && operator_character != '-') {
                return value;
            }
            ++position;
            double right = parse_mul_div();
            value = checked(operator_character == '+' ? value + right : value - right);
        }
    }

    double parse_mul_div() {
        double value = parse_unary();
        while (true) {
            skip_whitespace();
            char operator_character = current();
            if (operator_character != '*' && operator_character != '/' && operator_character != '%') {
                return value;
            }
            ++position;
            double right = parse_unary();
            if ((operator_character == '/' || operator_character == '%') && right == 0.0) {
                fail("division or remainder by zero");
            }
            if (operator_character == '*') {
                value = checked(value * right);
            } else if (operator_character == '/') {
                value = checked(value / right);
            } else {
                value = checked(std::fmod(value, right));
            }
        }
    }

    double parse_unary() {
        skip_whitespace();
        char operator_character = current();
        if (operator_character == '+' || operator_character == '-') {
            ++position;
            double value = parse_unary();
            return checked(operator_character == '-' ? -value : value);
        }
        return parse_power();
    }

    double parse_power() {
        double base = parse_primary();
        skip_whitespace();
        if (current() != '^') {
            return base;
        }
        ++position;
        double exponent = parse_unary();
        return checked(std::pow(base, exponent));
    }

    double parse_primary() {
        skip_whitespace();
        if (current() == '(') {
            ++position;
            double value = parse_add_sub();
            skip_whitespace();
            if (current() != ')') {
                fail("expected ')'");
            }
            ++position;
            return value;
        }
        return parse_number();
    }

    double parse_number() {
        skip_whitespace();
        std::size_t start = position;

        while (!at_end() && is_digit(current())) {
            ++position;
        }
        bool digits_before = position > start;

        bool digits_after = false;
        if (current() == '.') {
            ++position;
            std::size_t fraction_start = position;
            while (!at_end() && is_digit(current())) {
                ++position;
            }
            digits_after = position > fraction_start;
        }

        if (!digits_before && !digits_after) {
            fail("expected number");
        }

        if (current() == 'e' || current() == 'E') {
            ++position;
            if (current() == '+' || current() == '-') {
                ++position;
            }
            std::size_t exponent_start = position;
            while (!at_end() && is_digit(current())) {
                ++position;
            }
            if (position == exponent_start) {
                fail("invalid exponent");
            }
        }

        std::string token = input.substr(start, position - start);
        std::size_t parsed = 0;
        double value;
        try {
            value = std::stod(token, &parsed);
        } catch (const std::exception&) {
            fail("invalid number");
        }
        if (parsed != token.size()) {
            fail("invalid number");
        }
        return checked(value);
    }
};

int main(int argc, char** argv) {
    try {
        if (argc != 2) {
            throw std::runtime_error("expected exactly one expression argument");
        }
        Parser parser(argv[1]);
        double result = parser.parse();
        std::cout.imbue(std::locale::classic());
        std::cout << std::setprecision(std::numeric_limits<double>::max_digits10)
                  << result << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "error: " << error.what() << '\n';
        return 1;
    }
}
