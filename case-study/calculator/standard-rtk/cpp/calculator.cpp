#include <cmath>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>

class Parser {
public:
    explicit Parser(std::string text) : text_(std::move(text)) {}

    double parse() {
        double value = additive();
        skipSpace();
        if (pos_ != text_.size()) fail("unexpected token");
        return value;
    }

private:
    std::string text_;
    std::size_t pos_ = 0;

    void skipSpace() {
        while (pos_ < text_.size() && (text_[pos_] == ' ' || text_[pos_] == '\t' ||
               text_[pos_] == '\n' || text_[pos_] == '\r' || text_[pos_] == '\v' || text_[pos_] == '\f')) ++pos_;
    }

    bool take(char c) {
        skipSpace();
        if (pos_ < text_.size() && text_[pos_] == c) { ++pos_; return true; }
        return false;
    }

    [[noreturn]] static void fail(const char* message) { throw std::runtime_error(message); }

    static double checked(double value) {
        if (!std::isfinite(value)) fail("non-finite result");
        return value;
    }

    double additive() {
        double value = multiplicative();
        for (;;) {
            if (take('+')) value = checked(value + multiplicative());
            else if (take('-')) value = checked(value - multiplicative());
            else return value;
        }
    }

    double multiplicative() {
        double value = unary();
        for (;;) {
            if (take('*')) value = checked(value * unary());
            else if (take('/')) {
                double divisor = unary();
                if (divisor == 0.0) fail("division by zero");
                value = checked(value / divisor);
            } else if (take('%')) {
                double divisor = unary();
                if (divisor == 0.0) fail("remainder by zero");
                value = checked(std::fmod(value, divisor));
            } else return value;
        }
    }

    double unary() {
        if (take('+')) return unary();
        if (take('-')) return checked(-unary());
        return power();
    }

    double power() {
        double value = primary();
        if (take('^')) value = checked(std::pow(value, unary()));
        return value;
    }

    double primary() {
        if (take('(')) {
            double value = additive();
            if (!take(')')) fail("expected closing parenthesis");
            return value;
        }
        return number();
    }

    double number() {
        skipSpace();
        std::size_t start = pos_, before = 0, after = 0;
        while (pos_ < text_.size() && text_[pos_] >= '0' && text_[pos_] <= '9') { ++pos_; ++before; }
        if (pos_ < text_.size() && text_[pos_] == '.') {
            ++pos_;
            while (pos_ < text_.size() && text_[pos_] >= '0' && text_[pos_] <= '9') { ++pos_; ++after; }
        }
        if (before == 0 && after == 0) fail("expected number");
        if (pos_ < text_.size() && (text_[pos_] == 'e' || text_[pos_] == 'E')) {
            ++pos_;
            if (pos_ < text_.size() && (text_[pos_] == '+' || text_[pos_] == '-')) ++pos_;
            std::size_t exponentStart = pos_;
            while (pos_ < text_.size() && text_[pos_] >= '0' && text_[pos_] <= '9') ++pos_;
            if (pos_ == exponentStart) fail("malformed exponent");
        }
        char* end = nullptr;
        double value = std::strtod(text_.substr(start, pos_ - start).c_str(), &end);
        return checked(value);
    }
};

int main(int argc, char** argv) {
    if (argc != 2) {
        std::cerr << "error: expected exactly one expression\n";
        return 1;
    }
    try {
        double value = Parser(argv[1]).parse();
        std::cout << std::setprecision(std::numeric_limits<double>::max_digits10) << value << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "error: " << error.what() << '\n';
        return 1;
    }
}
