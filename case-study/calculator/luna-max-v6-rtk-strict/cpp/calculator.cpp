#include <cmath>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <string_view>

class Parser {
public:
    explicit Parser(std::string_view input) : input_(input) {}

    double parse() {
        double value = parseAdditive();
        skipWhitespace();
        if (position_ != input_.size()) {
            throw std::runtime_error("trailing tokens");
        }
        return checked(value);
    }

private:
    std::string_view input_;
    std::size_t position_ = 0;

    static bool isDigit(char character) {
        return character >= '0' && character <= '9';
    }

    static bool isWhitespace(char character) {
        return character == ' ' || character == '\t' || character == '\n' ||
               character == '\r' || character == '\f' || character == '\v';
    }

    void skipWhitespace() {
        while (position_ < input_.size() && isWhitespace(input_[position_])) {
            ++position_;
        }
    }

    char peek() {
        skipWhitespace();
        return position_ == input_.size() ? '\0' : input_[position_];
    }

    static double checked(double value) {
        if (!std::isfinite(value)) {
            throw std::runtime_error("non-finite result");
        }
        return value;
    }

    double parseAdditive() {
        double left = parseMultiplicative();
        while (true) {
            const char operation = peek();
            if (operation != '+' && operation != '-') {
                return left;
            }
            ++position_;
            const double right = parseMultiplicative();
            left = checked(operation == '+' ? left + right : left - right);
        }
    }

    double parseMultiplicative() {
        double left = parseUnary();
        while (true) {
            const char operation = peek();
            if (operation != '*' && operation != '/' && operation != '%') {
                return left;
            }
            ++position_;
            const double right = parseUnary();
            if ((operation == '/' || operation == '%') && right == 0.0) {
                throw std::runtime_error("division or remainder by zero");
            }
            double result;
            if (operation == '*') {
                result = left * right;
            } else if (operation == '/') {
                result = left / right;
            } else {
                result = std::fmod(left, right);
            }
            left = checked(result);
        }
    }

    double parseUnary() {
        const char operation = peek();
        if (operation == '+' || operation == '-') {
            ++position_;
            const double value = parseUnary();
            return checked(operation == '+' ? value : -value);
        }
        return parsePower();
    }

    double parsePower() {
        const double base = parsePrimary();
        if (peek() == '^') {
            ++position_;
            const double exponent = parseUnary();
            return checked(std::pow(base, exponent));
        }
        return base;
    }

    double parsePrimary() {
        if (peek() == '(') {
            ++position_;
            const double value = parseAdditive();
            if (peek() != ')') {
                throw std::runtime_error("missing closing parenthesis");
            }
            ++position_;
            return value;
        }
        return parseNumber();
    }

    double parseNumber() {
        skipWhitespace();
        const std::size_t start = position_;
        std::size_t digitsBefore = 0;
        while (position_ < input_.size() && isDigit(input_[position_])) {
            ++position_;
            ++digitsBefore;
        }

        std::size_t digitsAfter = 0;
        if (position_ < input_.size() && input_[position_] == '.') {
            ++position_;
            while (position_ < input_.size() && isDigit(input_[position_])) {
                ++position_;
                ++digitsAfter;
            }
        }

        if (digitsBefore == 0 && digitsAfter == 0) {
            throw std::runtime_error("expected number or parenthesis");
        }

        if (position_ < input_.size() &&
            (input_[position_] == 'e' || input_[position_] == 'E')) {
            ++position_;
            if (position_ < input_.size() &&
                (input_[position_] == '+' || input_[position_] == '-')) {
                ++position_;
            }
            const std::size_t exponentStart = position_;
            while (position_ < input_.size() && isDigit(input_[position_])) {
                ++position_;
            }
            if (position_ == exponentStart) {
                throw std::runtime_error("malformed exponent");
            }
        }

        const std::string token(input_.substr(start, position_ - start));
        std::size_t consumed = 0;
        const double value = std::stod(token, &consumed);
        if (consumed != token.size()) {
            throw std::runtime_error("invalid number");
        }
        return checked(value);
    }
};

int main(int argc, char** argv) {
    try {
        if (argc != 2) {
            throw std::runtime_error("expected exactly one expression argument");
        }
        const double result = Parser(argv[1]).parse();
        std::cout << std::setprecision(17) << result << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "error: " << error.what() << '\n';
        return 1;
    }
}
