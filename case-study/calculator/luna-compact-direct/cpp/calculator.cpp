#include <cmath>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <string_view>

class CalculatorError : public std::runtime_error {
public:
    explicit CalculatorError(const char* message) : std::runtime_error(message) {}
};

class Parser {
public:
    explicit Parser(std::string_view source) : source_(source) {}

    double evaluate() {
        const double result = parse_sum();
        skip_whitespace();
        if (position_ != source_.size()) {
            throw CalculatorError("unexpected trailing input");
        }
        return result;
    }

private:
    std::string_view source_;
    std::size_t position_ = 0;

    static bool is_digit(char value) {
        return value >= '0' && value <= '9';
    }

    static bool is_whitespace(char value) {
        return value == ' ' || value == '\t' || value == '\n' || value == '\r'
            || value == '\v' || value == '\f';
    }

    void skip_whitespace() {
        while (position_ < source_.size() && is_whitespace(source_[position_])) {
            ++position_;
        }
    }

    bool take(char token) {
        skip_whitespace();
        if (position_ < source_.size() && source_[position_] == token) {
            ++position_;
            return true;
        }
        return false;
    }

    static double finite(double value) {
        if (!std::isfinite(value)) {
            throw CalculatorError("non-finite result");
        }
        return value;
    }

    double parse_sum() {
        double result = parse_product();
        while (true) {
            if (take('+')) {
                result = finite(result + parse_product());
            } else if (take('-')) {
                result = finite(result - parse_product());
            } else {
                return result;
            }
        }
    }

    double parse_product() {
        double result = parse_unary();
        while (true) {
            if (take('*')) {
                result = finite(result * parse_unary());
            } else if (take('/')) {
                const double divisor = parse_unary();
                if (divisor == 0.0) {
                    throw CalculatorError("division by zero");
                }
                result = finite(result / divisor);
            } else if (take('%')) {
                const double divisor = parse_unary();
                if (divisor == 0.0) {
                    throw CalculatorError("remainder by zero");
                }
                result = finite(std::fmod(result, divisor));
            } else {
                return result;
            }
        }
    }

    double parse_unary() {
        if (take('+')) {
            return parse_unary();
        }
        if (take('-')) {
            return finite(-parse_unary());
        }
        return parse_power();
    }

    double parse_power() {
        const double base = parse_primary();
        if (take('^')) {
            return finite(std::pow(base, parse_unary()));
        }
        return base;
    }

    double parse_primary() {
        if (take('(')) {
            const double result = parse_sum();
            if (!take(')')) {
                throw CalculatorError("expected closing parenthesis");
            }
            return result;
        }
        return parse_number();
    }

    double parse_number() {
        skip_whitespace();
        const std::size_t start = position_;
        std::size_t digit_count = 0;

        while (position_ < source_.size() && is_digit(source_[position_])) {
            ++position_;
            ++digit_count;
        }
        if (position_ < source_.size() && source_[position_] == '.') {
            ++position_;
            while (position_ < source_.size() && is_digit(source_[position_])) {
                ++position_;
                ++digit_count;
            }
        }
        if (digit_count == 0) {
            throw CalculatorError("expected number");
        }

        if (position_ < source_.size() && (source_[position_] == 'e' || source_[position_] == 'E')) {
            ++position_;
            if (position_ < source_.size() && (source_[position_] == '+' || source_[position_] == '-')) {
                ++position_;
            }
            const std::size_t exponent_start = position_;
            while (position_ < source_.size() && is_digit(source_[position_])) {
                ++position_;
            }
            if (position_ == exponent_start) {
                throw CalculatorError("malformed exponent");
            }
        }

        const std::string token(source_.substr(start, position_ - start));
        std::size_t parsed = 0;
        try {
            const double value = std::stod(token, &parsed);
            if (parsed != token.size()) {
                throw CalculatorError("invalid number");
            }
            return finite(value);
        } catch (const std::invalid_argument&) {
            throw CalculatorError("invalid number");
        } catch (const std::out_of_range&) {
            throw CalculatorError("non-finite result");
        }
    }
};

int main(int argc, char** argv) {
    if (argc != 2) {
        std::cerr << "error: expected exactly one expression argument\n";
        return 1;
    }

    try {
        const double result = Parser(argv[1]).evaluate();
        std::cout << std::setprecision(std::numeric_limits<double>::max_digits10)
                  << result << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "error: " << error.what() << '\n';
        return 1;
    }
}
