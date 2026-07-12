#include <cmath>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <string_view>

class CalculatorError : public std::runtime_error {
public:
    using std::runtime_error::runtime_error;
};

class Parser {
public:
    explicit Parser(std::string_view expression) : input_(expression) {}

    double parse() {
        double value = parseAddition();
        skipWhitespace();
        if (position_ != input_.size()) {
            throw CalculatorError("unexpected trailing token");
        }
        return value;
    }

private:
    double parseAddition() {
        double value = parseMultiplication();
        while (true) {
            if (consume('+')) {
                value = checked(value + parseMultiplication());
            } else if (consume('-')) {
                value = checked(value - parseMultiplication());
            } else {
                return value;
            }
        }
    }

    double parseMultiplication() {
        double value = parseUnary();
        while (true) {
            if (consume('*')) {
                value = checked(value * parseUnary());
            } else if (consume('/')) {
                double right = parseUnary();
                if (right == 0.0) {
                    throw CalculatorError("division by zero");
                }
                value = checked(value / right);
            } else if (consume('%')) {
                double right = parseUnary();
                if (right == 0.0) {
                    throw CalculatorError("remainder by zero");
                }
                value = checked(std::fmod(value, right));
            } else {
                return value;
            }
        }
    }

    double parseUnary() {
        if (consume('+')) {
            return parseUnary();
        }
        if (consume('-')) {
            return -parseUnary();
        }
        return parsePower();
    }

    double parsePower() {
        double value = parsePrimary();
        if (consume('^')) {
            double exponent = parseUnary();
            return checked(std::pow(value, exponent));
        }
        return value;
    }

    double parsePrimary() {
        skipWhitespace();
        if (position_ == input_.size()) {
            throw CalculatorError("expected a number or parenthesized expression");
        }

        if (input_[position_] == '(') {
            ++position_;
            double value = parseAddition();
            if (!consume(')')) {
                throw CalculatorError("missing closing parenthesis");
            }
            return value;
        }

        char character = input_[position_];
        if (isDigit(character) || character == '.') {
            return parseNumber();
        }
        throw CalculatorError("expected a number or parenthesized expression");
    }

    double parseNumber() {
        const std::size_t start = position_;
        std::size_t digitsBeforeDecimal = 0;
        while (position_ < input_.size() && isDigit(input_[position_])) {
            ++position_;
            ++digitsBeforeDecimal;
        }

        std::size_t digitsAfterDecimal = 0;
        if (position_ < input_.size() && input_[position_] == '.') {
            ++position_;
            while (position_ < input_.size() && isDigit(input_[position_])) {
                ++position_;
                ++digitsAfterDecimal;
            }
        }

        if (digitsBeforeDecimal == 0 && digitsAfterDecimal == 0) {
            throw CalculatorError("invalid number");
        }

        if (position_ < input_.size() &&
            (input_[position_] == 'e' || input_[position_] == 'E')) {
            ++position_;
            if (position_ < input_.size() &&
                (input_[position_] == '+' || input_[position_] == '-')) {
                ++position_;
            }
            std::size_t exponentDigits = 0;
            while (position_ < input_.size() && isDigit(input_[position_])) {
                ++position_;
                ++exponentDigits;
            }
            if (exponentDigits == 0) {
                throw CalculatorError("invalid exponent");
            }
        }

        const std::string literal(input_.substr(start, position_ - start));
        std::size_t consumed = 0;
        double value = 0.0;
        try {
            value = std::stod(literal, &consumed);
        } catch (const std::exception&) {
            throw CalculatorError("invalid number");
        }
        if (consumed != literal.size()) {
            throw CalculatorError("invalid number");
        }
        return checked(value);
    }

    bool consume(char token) {
        skipWhitespace();
        if (position_ < input_.size() && input_[position_] == token) {
            ++position_;
            return true;
        }
        return false;
    }

    void skipWhitespace() {
        while (position_ < input_.size() && isWhitespace(input_[position_])) {
            ++position_;
        }
    }

    static bool isDigit(char character) {
        return character >= '0' && character <= '9';
    }

    static bool isWhitespace(char character) {
        return character == ' ' || character == '\t' || character == '\n' ||
               character == '\r' || character == '\v' || character == '\f';
    }

    static double checked(double value) {
        if (!std::isfinite(value)) {
            throw CalculatorError("non-finite result");
        }
        return value;
    }

    std::string_view input_;
    std::size_t position_ = 0;
};

int main(int argc, char* argv[]) {
    if (argc != 2) {
        std::cerr << "error: expected exactly one expression argument\n";
        return 1;
    }

    try {
        const double result = Parser(argv[1]).parse();
        std::cout << std::setprecision(std::numeric_limits<double>::max_digits10)
                  << result << '\n';
        return 0;
    } catch (const CalculatorError& error) {
        std::cerr << "error: " << error.what() << '\n';
        return 1;
    } catch (const std::exception&) {
        std::cerr << "error: invalid expression\n";
        return 1;
    }
}
