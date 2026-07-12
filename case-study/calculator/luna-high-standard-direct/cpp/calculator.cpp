#include <cmath>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>

class CalculatorError : public std::runtime_error {
public:
    explicit CalculatorError(const std::string& message) : std::runtime_error(message) {}
};

class Parser {
public:
    explicit Parser(const std::string& text) : text_(text) {}

    double parse() {
        double value = parse_additive();
        skip_space();
        if (pos_ != text_.size()) {
            throw CalculatorError("unexpected trailing input");
        }
        return value;
    }

private:
    const std::string& text_;
    std::size_t pos_ = 0;

    void skip_space() {
        while (pos_ < text_.size() && is_space(text_[pos_])) {
            ++pos_;
        }
    }

    static bool is_space(char value) {
        return value == ' ' || value == '\t' || value == '\n' || value == '\r' || value == '\v' || value == '\f';
    }

    static bool is_digit(char value) {
        return value >= '0' && value <= '9';
    }

    bool consume(char token) {
        skip_space();
        if (pos_ < text_.size() && text_[pos_] == token) {
            ++pos_;
            return true;
        }
        return false;
    }

    static double finite(double value) {
        if (!std::isfinite(value)) {
            throw CalculatorError("non-finite input or result");
        }
        return value;
    }

    double parse_additive() {
        double value = parse_multiplicative();
        while (true) {
            if (consume('+')) {
                value = finite(value + parse_multiplicative());
            } else if (consume('-')) {
                value = finite(value - parse_multiplicative());
            } else {
                return value;
            }
        }
    }

    double parse_multiplicative() {
        double value = parse_unary();
        while (true) {
            if (consume('*')) {
                value = finite(value * parse_unary());
            } else if (consume('/')) {
                double divisor = parse_unary();
                if (divisor == 0.0) {
                    throw CalculatorError("division by zero");
                }
                value = finite(value / divisor);
            } else if (consume('%')) {
                double divisor = parse_unary();
                if (divisor == 0.0) {
                    throw CalculatorError("remainder by zero");
                }
                value = finite(std::fmod(value, divisor));
            } else {
                return value;
            }
        }
    }

    double parse_unary() {
        if (consume('+')) {
            return parse_unary();
        }
        if (consume('-')) {
            return finite(-parse_unary());
        }
        return parse_power();
    }

    double parse_power() {
        double value = parse_primary();
        if (consume('^')) {
            return finite(std::pow(value, parse_unary()));
        }
        return value;
    }

    double parse_primary() {
        if (consume('(')) {
            double value = parse_additive();
            if (!consume(')')) {
                throw CalculatorError("expected closing parenthesis");
            }
            return value;
        }
        return parse_number();
    }

    double parse_number() {
        skip_space();
        const std::size_t start = pos_;
        std::size_t digits = 0;
        while (pos_ < text_.size() && is_digit(text_[pos_])) {
            ++pos_;
            ++digits;
        }
        if (pos_ < text_.size() && text_[pos_] == '.') {
            ++pos_;
            while (pos_ < text_.size() && is_digit(text_[pos_])) {
                ++pos_;
                ++digits;
            }
        }
        if (digits == 0) {
            throw CalculatorError("expected number");
        }
        if (pos_ < text_.size() && (text_[pos_] == 'e' || text_[pos_] == 'E')) {
            ++pos_;
            if (pos_ < text_.size() && (text_[pos_] == '+' || text_[pos_] == '-')) {
                ++pos_;
            }
            const std::size_t exponent_start = pos_;
            while (pos_ < text_.size() && is_digit(text_[pos_])) {
                ++pos_;
            }
            if (pos_ == exponent_start) {
                throw CalculatorError("malformed exponent");
            }
        }

        const std::string token = text_.substr(start, pos_ - start);
        char* end = nullptr;
        const double value = std::strtod(token.c_str(), &end);
        if (end != token.c_str() + token.size()) {
            throw CalculatorError("invalid number");
        }
        return finite(value);
    }
};

int main(int argc, char** argv) {
    if (argc != 2) {
        std::cerr << "error: expected exactly one expression argument\n";
        return 1;
    }
    try {
        const double result = Parser(argv[1]).parse();
        std::cout << std::setprecision(std::numeric_limits<double>::max_digits10) << result << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "error: " << error.what() << '\n';
        return 1;
    }
}
