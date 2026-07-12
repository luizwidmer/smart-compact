#include <cmath>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>

class Parser {
public:
    explicit Parser(std::string source) : source_(std::move(source)) {}

    double parse() {
        double value = additive();
        skip_space();
        if (pos_ != source_.size()) fail("unexpected token");
        return value;
    }

private:
    std::string source_;
    std::size_t pos_ = 0;

    [[noreturn]] void fail(const char* message) const { throw std::runtime_error(message); }

    static bool is_space(char c) {
        return c == ' ' || c == '\t' || c == '\n' || c == '\r' || c == '\v' || c == '\f';
    }

    void skip_space() {
        while (pos_ < source_.size() && is_space(source_[pos_])) ++pos_;
    }

    double number() {
        skip_space();
        const std::size_t start = pos_;
        std::size_t before = 0;
        while (pos_ < source_.size() && source_[pos_] >= '0' && source_[pos_] <= '9') { ++pos_; ++before; }
        std::size_t after = 0;
        if (pos_ < source_.size() && source_[pos_] == '.') {
            ++pos_;
            while (pos_ < source_.size() && source_[pos_] >= '0' && source_[pos_] <= '9') { ++pos_; ++after; }
        }
        if (before + after == 0) fail("expected number");
        if (pos_ < source_.size() && (source_[pos_] == 'e' || source_[pos_] == 'E')) {
            ++pos_;
            if (pos_ < source_.size() && (source_[pos_] == '+' || source_[pos_] == '-')) ++pos_;
            const std::size_t exponent_start = pos_;
            while (pos_ < source_.size() && source_[pos_] >= '0' && source_[pos_] <= '9') ++pos_;
            if (pos_ == exponent_start) fail("invalid exponent");
        }
        char* end = nullptr;
        const std::string raw = source_.substr(start, pos_ - start);
        const double value = std::strtod(raw.c_str(), &end);
        if (end == raw.c_str() || *end != '\0') fail("invalid number");
        if (!std::isfinite(value)) fail("non-finite number");
        return value;
    }

    double primary() {
        skip_space();
        if (pos_ < source_.size() && source_[pos_] == '(') {
            ++pos_;
            double value = additive();
            skip_space();
            if (pos_ == source_.size() || source_[pos_] != ')') fail("expected ')'");
            ++pos_;
            return value;
        }
        return number();
    }

    double power() {
        double value = primary();
        skip_space();
        if (pos_ < source_.size() && source_[pos_] == '^') {
            ++pos_;
            value = std::pow(value, unary());
            if (!std::isfinite(value)) fail("non-finite result");
        }
        return value;
    }

    double unary() {
        skip_space();
        if (pos_ < source_.size() && (source_[pos_] == '+' || source_[pos_] == '-')) {
            const bool negative = source_[pos_] == '-';
            ++pos_;
            const double value = unary();
            return negative ? -value : value;
        }
        return power();
    }

    double multiplicative() {
        double value = unary();
        while (true) {
            skip_space();
            if (pos_ == source_.size() || (source_[pos_] != '*' && source_[pos_] != '/' && source_[pos_] != '%')) return value;
            const char operation = source_[pos_++];
            const double right = unary();
            if (right == 0.0) fail("division by zero");
            if (operation == '*') value *= right;
            else if (operation == '/') value /= right;
            else value = std::fmod(value, right);
            if (!std::isfinite(value)) fail("non-finite result");
        }
    }

    double additive() {
        double value = multiplicative();
        while (true) {
            skip_space();
            if (pos_ == source_.size() || (source_[pos_] != '+' && source_[pos_] != '-')) return value;
            const char operation = source_[pos_++];
            const double right = multiplicative();
            value = operation == '+' ? value + right : value - right;
            if (!std::isfinite(value)) fail("non-finite result");
        }
    }
};

int main(int argc, char** argv) {
    if (argc != 2) {
        std::cerr << "error: expected exactly one expression\n";
        return 1;
    }
    try {
        const double result = Parser(argv[1]).parse();
        std::cout << std::setprecision(17) << result << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "error: " << error.what() << '\n';
        return 1;
    }
}
