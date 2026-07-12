#include <cmath>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>

class Parser {
    const std::string& input;
    std::size_t pos = 0;

    void skipSpace() {
        while (pos < input.size()) {
            char c = input[pos];
            if (c != ' ' && c != '\t' && c != '\n' && c != '\r' && c != '\f' && c != '\v') break;
            ++pos;
        }
    }

    bool take(char token) {
        skipSpace();
        if (pos < input.size() && input[pos] == token) {
            ++pos;
            return true;
        }
        return false;
    }

    static double checked(double value) {
        if (!std::isfinite(value)) throw std::runtime_error("non-finite result");
        return value;
    }

    double additive() {
        double value = multiplicative();
        while (true) {
            if (take('+')) value = checked(value + multiplicative());
            else if (take('-')) value = checked(value - multiplicative());
            else return value;
        }
    }

    double multiplicative() {
        double value = unary();
        while (true) {
            if (take('*')) value = checked(value * unary());
            else if (take('/')) {
                double divisor = unary();
                if (divisor == 0.0) throw std::runtime_error("division by zero");
                value = checked(value / divisor);
            } else if (take('%')) {
                double divisor = unary();
                if (divisor == 0.0) throw std::runtime_error("remainder by zero");
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
        double base = primary();
        return take('^') ? checked(std::pow(base, unary())) : base;
    }

    double primary() {
        if (take('(')) {
            double value = additive();
            if (!take(')')) throw std::runtime_error("expected ')'");
            return value;
        }
        return number();
    }

    double number() {
        skipSpace();
        std::size_t start = pos;
        std::size_t digits = 0;
        while (pos < input.size() && input[pos] >= '0' && input[pos] <= '9') { ++pos; ++digits; }
        if (pos < input.size() && input[pos] == '.') {
            ++pos;
            while (pos < input.size() && input[pos] >= '0' && input[pos] <= '9') { ++pos; ++digits; }
        }
        if (digits == 0) throw std::runtime_error("expected number");
        if (pos < input.size() && (input[pos] == 'e' || input[pos] == 'E')) {
            ++pos;
            if (pos < input.size() && (input[pos] == '+' || input[pos] == '-')) ++pos;
            std::size_t exponentStart = pos;
            while (pos < input.size() && input[pos] >= '0' && input[pos] <= '9') ++pos;
            if (pos == exponentStart) throw std::runtime_error("malformed exponent");
        }
        std::string token = input.substr(start, pos - start);
        char* end = nullptr;
        double value = std::strtod(token.c_str(), &end);
        if (end != token.c_str() + token.size()) throw std::runtime_error("invalid number");
        if (!std::isfinite(value)) throw std::runtime_error("non-finite input");
        return value;
    }

public:
    explicit Parser(const std::string& text) : input(text) {}

    double parse() {
        double value = additive();
        skipSpace();
        if (pos != input.size()) throw std::runtime_error("unexpected trailing input");
        return value;
    }
};

int main(int argc, char* argv[]) {
    if (argc != 2) {
        std::cerr << "error: expected exactly one expression\n";
        return 1;
    }
    try {
        std::cout << std::setprecision(17) << Parser(argv[1]).parse() << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "error: " << error.what() << '\n';
        return 1;
    }
}
