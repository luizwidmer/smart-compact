#include <cmath>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>

class CalculatorError : public std::runtime_error {
public:
    using std::runtime_error::runtime_error;
};

class Parser {
    const std::string& input_;
    std::size_t pos_ = 0;

    void skipWhitespace() {
        while (pos_ < input_.size()) {
            const char c = input_[pos_];
            if (c == ' ' || c == '\t' || c == '\n' || c == '\r' || c == '\f' || c == '\v') ++pos_;
            else break;
        }
    }

    bool consume(char token) {
        skipWhitespace();
        if (pos_ < input_.size() && input_[pos_] == token) {
            ++pos_;
            return true;
        }
        return false;
    }

    static double checked(double value) {
        if (!std::isfinite(value)) throw CalculatorError("non-finite result");
        return value;
    }

    double expression() {
        double value = term();
        for (;;) {
            if (consume('+')) value = checked(value + term());
            else if (consume('-')) value = checked(value - term());
            else return value;
        }
    }

    double term() {
        double value = unary();
        for (;;) {
            if (consume('*')) value = checked(value * unary());
            else if (consume('/')) {
                const double divisor = unary();
                if (divisor == 0.0) throw CalculatorError("division by zero");
                value = checked(value / divisor);
            } else if (consume('%')) {
                const double divisor = unary();
                if (divisor == 0.0) throw CalculatorError("remainder by zero");
                value = checked(std::fmod(value, divisor));
            } else return value;
        }
    }

    double unary() {
        if (consume('+')) return checked(unary());
        if (consume('-')) return checked(-unary());
        return power();
    }

    double power() {
        const double base = primary();
        if (consume('^')) return checked(std::pow(base, unary()));
        return base;
    }

    double primary() {
        if (consume('(')) {
            const double value = expression();
            if (!consume(')')) throw CalculatorError("expected ')'");
            return value;
        }
        return number();
    }

    double number() {
        skipWhitespace();
        const std::size_t start = pos_;
        std::size_t digits = 0;
        while (pos_ < input_.size() && input_[pos_] >= '0' && input_[pos_] <= '9') { ++pos_; ++digits; }
        if (pos_ < input_.size() && input_[pos_] == '.') {
            ++pos_;
            while (pos_ < input_.size() && input_[pos_] >= '0' && input_[pos_] <= '9') { ++pos_; ++digits; }
        }
        if (digits == 0) throw CalculatorError("expected number");
        if (pos_ < input_.size() && (input_[pos_] == 'e' || input_[pos_] == 'E')) {
            ++pos_;
            if (pos_ < input_.size() && (input_[pos_] == '+' || input_[pos_] == '-')) ++pos_;
            const std::size_t exponentStart = pos_;
            while (pos_ < input_.size() && input_[pos_] >= '0' && input_[pos_] <= '9') ++pos_;
            if (pos_ == exponentStart) throw CalculatorError("malformed exponent");
        }
        try {
            return checked(std::stod(input_.substr(start, pos_ - start)));
        } catch (const std::out_of_range&) {
            throw CalculatorError("non-finite input");
        } catch (const std::invalid_argument&) {
            throw CalculatorError("invalid number");
        }
    }

public:
    explicit Parser(const std::string& input) : input_(input) {}

    double parse() {
        const double value = expression();
        skipWhitespace();
        if (pos_ != input_.size()) throw CalculatorError("unexpected trailing input");
        return value;
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
