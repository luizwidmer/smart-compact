#include <cmath>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>

class Parser {
public:
    explicit Parser(const std::string& input) : input_(input) {}

    double parse() {
        double value = additive();
        skipSpace();
        if (pos_ != input_.size()) fail("unexpected trailing input");
        return value;
    }

private:
    const std::string& input_;
    std::size_t pos_ = 0;

    [[noreturn]] static void fail(const char* message) { throw std::runtime_error(message); }

    static double finite(double value) {
        if (!std::isfinite(value)) fail("non-finite result");
        return value;
    }

    void skipSpace() {
        while (pos_ < input_.size()) {
            char c = input_[pos_];
            if (c != ' ' && c != '\t' && c != '\n' && c != '\r' && c != '\v' && c != '\f') break;
            ++pos_;
        }
    }

    bool consume(char token) {
        skipSpace();
        if (pos_ < input_.size() && input_[pos_] == token) {
            ++pos_;
            return true;
        }
        return false;
    }

    double additive() {
        double value = multiplicative();
        while (true) {
            if (consume('+')) value = finite(value + multiplicative());
            else if (consume('-')) value = finite(value - multiplicative());
            else return value;
        }
    }

    double multiplicative() {
        double value = unary();
        while (true) {
            if (consume('*')) value = finite(value * unary());
            else if (consume('/')) {
                double divisor = unary();
                if (divisor == 0.0) fail("division by zero");
                value = finite(value / divisor);
            } else if (consume('%')) {
                double divisor = unary();
                if (divisor == 0.0) fail("remainder by zero");
                value = finite(std::fmod(value, divisor));
            } else return value;
        }
    }

    double unary() {
        if (consume('+')) return unary();
        if (consume('-')) return finite(-unary());
        return power();
    }

    double power() {
        double value = primary();
        if (consume('^')) value = finite(std::pow(value, unary()));
        return value;
    }

    double primary() {
        if (consume('(')) {
            double value = additive();
            if (!consume(')')) fail("expected closing parenthesis");
            return value;
        }
        return number();
    }

    double number() {
        skipSpace();
        std::size_t start = pos_;
        int digits = 0;
        while (pos_ < input_.size() && input_[pos_] >= '0' && input_[pos_] <= '9') { ++pos_; ++digits; }
        if (pos_ < input_.size() && input_[pos_] == '.') {
            ++pos_;
            while (pos_ < input_.size() && input_[pos_] >= '0' && input_[pos_] <= '9') { ++pos_; ++digits; }
        }
        if (digits == 0) fail("expected number");
        if (pos_ < input_.size() && (input_[pos_] == 'e' || input_[pos_] == 'E')) {
            ++pos_;
            if (pos_ < input_.size() && (input_[pos_] == '+' || input_[pos_] == '-')) ++pos_;
            std::size_t exponentStart = pos_;
            while (pos_ < input_.size() && input_[pos_] >= '0' && input_[pos_] <= '9') ++pos_;
            if (pos_ == exponentStart) fail("malformed exponent");
        }
        double value = std::stod(input_.substr(start, pos_ - start));
        return finite(value);
    }
};

int main(int argc, char** argv) {
    if (argc != 2) {
        std::cerr << "error: expected exactly one expression argument\n";
        return 1;
    }
    try {
        double result = Parser(argv[1]).parse();
        std::cout << std::setprecision(std::numeric_limits<double>::max_digits10) << result << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "error: " << error.what() << '\n';
        return 1;
    }
}
