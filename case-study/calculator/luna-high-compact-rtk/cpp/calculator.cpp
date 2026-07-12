#include <cmath>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>

struct CalcError : std::runtime_error { using std::runtime_error::runtime_error; };

class Parser {
    const std::string& text;
    std::size_t pos = 0;

    void whitespace() {
        while (pos < text.size() && (text[pos] == ' ' || text[pos] == '\t' || text[pos] == '\n' || text[pos] == '\r' || text[pos] == '\v' || text[pos] == '\f')) ++pos;
    }

    double number() {
        whitespace();
        const std::size_t start = pos;
        std::size_t digits = 0;
        while (pos < text.size() && text[pos] >= '0' && text[pos] <= '9') { ++pos; ++digits; }
        if (pos < text.size() && text[pos] == '.') {
            ++pos;
            while (pos < text.size() && text[pos] >= '0' && text[pos] <= '9') { ++pos; ++digits; }
        }
        if (digits == 0) { pos = start; throw CalcError("expected number"); }
        if (pos < text.size() && (text[pos] == 'e' || text[pos] == 'E')) {
            ++pos;
            if (pos < text.size() && (text[pos] == '+' || text[pos] == '-')) ++pos;
            const std::size_t exponent_start = pos;
            while (pos < text.size() && text[pos] >= '0' && text[pos] <= '9') ++pos;
            if (pos == exponent_start) throw CalcError("malformed exponent");
        }
        char* end = nullptr;
        const std::string raw = text.substr(start, pos - start);
        const double value = std::strtod(raw.c_str(), &end);
        if (end != raw.c_str() + raw.size()) throw CalcError("invalid number");
        if (!std::isfinite(value)) throw CalcError("non-finite number");
        return value;
    }

    double primary() {
        whitespace();
        if (pos < text.size() && text[pos] == '(') {
            ++pos;
            const double value = additive();
            whitespace();
            if (pos >= text.size() || text[pos] != ')') throw CalcError("expected closing parenthesis");
            ++pos;
            return value;
        }
        return number();
    }

    double power() {
        double value = primary();
        whitespace();
        if (pos < text.size() && text[pos] == '^') {
            ++pos;
            value = std::pow(value, unary());
            if (!std::isfinite(value)) throw CalcError("non-finite result");
        }
        return value;
    }

    double unary() {
        whitespace();
        if (pos < text.size() && (text[pos] == '+' || text[pos] == '-')) {
            const bool negative = text[pos] == '-';
            ++pos;
            const double value = unary();
            return negative ? -value : value;
        }
        return power();
    }

    double multiplicative() {
        double value = unary();
        for (;;) {
            whitespace();
            if (pos >= text.size() || (text[pos] != '*' && text[pos] != '/' && text[pos] != '%')) return value;
            const char op = text[pos++];
            const double right = unary();
            if (right == 0.0) throw CalcError("division by zero");
            if (op == '*') value *= right;
            else if (op == '/') value /= right;
            else value = std::fmod(value, right);
            if (!std::isfinite(value)) throw CalcError("non-finite result");
        }
    }

    double additive() {
        double value = multiplicative();
        for (;;) {
            whitespace();
            if (pos >= text.size() || (text[pos] != '+' && text[pos] != '-')) return value;
            const char op = text[pos++];
            const double right = multiplicative();
            value = op == '+' ? value + right : value - right;
            if (!std::isfinite(value)) throw CalcError("non-finite result");
        }
    }

public:
    explicit Parser(const std::string& input) : text(input) {}

    double parse() {
        whitespace();
        if (pos == text.size()) throw CalcError("empty expression");
        const double value = additive();
        whitespace();
        if (pos != text.size()) throw CalcError("trailing tokens");
        return value;
    }
};

int main(int argc, char** argv) {
    try {
        if (argc != 2) throw CalcError("expected exactly one expression");
        const double value = Parser(argv[1]).parse();
        std::cout << std::setprecision(std::numeric_limits<double>::max_digits10) << value << '\n';
        return 0;
    } catch (const CalcError& error) {
        std::cerr << "error: " << error.what() << '\n';
        return 1;
    }
}
