#include <cmath>
#include <cstdlib>
#include <exception>
#include <iomanip>
#include <iostream>
#include <limits>
#include <locale>
#include <stdexcept>
#include <string>

class Parser {
public:
    explicit Parser(const std::string& expression) : input(expression) {}

    double parse() {
        double value = parse_add_sub();
        skip_whitespace();
        if (position != input.size()) fail("trailing tokens");
        return checked(value);
    }

private:
    const std::string& input;
    std::size_t position = 0;

    static bool is_digit(char c) { return c >= '0' && c <= '9'; }
    static bool is_whitespace(char c) {
        return c == ' ' || c == '\t' || c == '\r' || c == '\n' || c == '\v' || c == '\f';
    }
    char current() const { return position < input.size() ? input[position] : '\0'; }
    void skip_whitespace() {
        while (position < input.size() && is_whitespace(current())) ++position;
    }
    static double checked(double value) {
        if (!std::isfinite(value)) fail("non-finite result");
        return value;
    }
    [[noreturn]] static void fail(const char* message) { throw std::runtime_error(message); }

    double parse_add_sub() {
        double value = parse_mul_div();
        while (true) {
            skip_whitespace();
            char operation = current();
            if (operation != '+' && operation != '-') return value;
            ++position;
            double right = parse_mul_div();
            value = checked(operation == '+' ? value + right : value - right);
        }
    }

    double parse_mul_div() {
        double value = parse_unary();
        while (true) {
            skip_whitespace();
            char operation = current();
            if (operation != '*' && operation != '/' && operation != '%') return value;
            ++position;
            double right = parse_unary();
            if ((operation == '/' || operation == '%') && right == 0.0) fail("division or remainder by zero");
            if (operation == '*') value = checked(value * right);
            else if (operation == '/') value = checked(value / right);
            else value = checked(std::fmod(value, right));
        }
    }

    double parse_unary() {
        skip_whitespace();
        char operation = current();
        if (operation == '+' || operation == '-') {
            ++position;
            double value = parse_unary();
            return checked(operation == '-' ? -value : value);
        }
        return parse_power();
    }

    double parse_power() {
        double base = parse_primary();
        skip_whitespace();
        if (current() != '^') return base;
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
            if (current() != ')') fail("expected ')' ");
            ++position;
            return value;
        }
        return parse_number();
    }

    double parse_number() {
        skip_whitespace();
        std::size_t start = position;
        while (position < input.size() && is_digit(current())) ++position;
        bool digits_before = position > start;
        bool digits_after = false;
        if (current() == '.') {
            ++position;
            std::size_t fraction_start = position;
            while (position < input.size() && is_digit(current())) ++position;
            digits_after = position > fraction_start;
        }
        if (!digits_before && !digits_after) fail("expected number");
        if (current() == 'e' || current() == 'E') {
            ++position;
            if (current() == '+' || current() == '-') ++position;
            std::size_t exponent_start = position;
            while (position < input.size() && is_digit(current())) ++position;
            if (position == exponent_start) fail("invalid exponent");
        }
        std::string token = input.substr(start, position - start);
        char* end = nullptr;
        double value = std::strtod(token.c_str(), &end);
        if (end != token.c_str() + token.size()) fail("invalid number");
        return checked(value);
    }
};

int main(int argc, char** argv) {
    try {
        if (argc != 2) throw std::runtime_error("expected exactly one expression argument");
        double result = Parser(argv[1]).parse();
        std::cout.imbue(std::locale::classic());
        std::cout << std::setprecision(std::numeric_limits<double>::max_digits10) << result << '\n';
    } catch (const std::exception& error) {
        std::cerr << "error: " << error.what() << '\n';
        return 1;
    }
    return 0;
}
