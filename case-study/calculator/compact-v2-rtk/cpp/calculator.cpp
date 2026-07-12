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
        while (pos < input.size() && (input[pos] == ' ' || input[pos] == '\t' || input[pos] == '\n' || input[pos] == '\r' || input[pos] == '\v' || input[pos] == '\f')) ++pos;
    }

    bool take(char token) {
        skipSpace();
        if (pos < input.size() && input[pos] == token) { ++pos; return true; }
        return false;
    }

    static double checked(double value) {
        if (!std::isfinite(value)) throw std::runtime_error("non-finite result");
        return value;
    }

    double expression() {
        double value = term();
        while (true) {
            if (take('+')) value = checked(value + term());
            else if (take('-')) value = checked(value - term());
            else return value;
        }
    }

    double term() {
        double value = unary();
        while (true) {
            if (take('*')) value = checked(value * unary());
            else if (take('/')) {
                double rhs = unary();
                if (rhs == 0.0) throw std::runtime_error("division by zero");
                value = checked(value / rhs);
            } else if (take('%')) {
                double rhs = unary();
                if (rhs == 0.0) throw std::runtime_error("remainder by zero");
                value = checked(std::fmod(value, rhs));
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
            double value = expression();
            if (!take(')')) throw std::runtime_error("missing closing parenthesis");
            return value;
        }
        return number();
    }

    double number() {
        skipSpace();
        std::size_t start = pos, digits = 0;
        while (pos < input.size() && input[pos] >= '0' && input[pos] <= '9') { ++pos; ++digits; }
        if (pos < input.size() && input[pos] == '.') {
            ++pos;
            while (pos < input.size() && input[pos] >= '0' && input[pos] <= '9') { ++pos; ++digits; }
        }
        if (digits == 0) throw std::runtime_error("expected number");
        if (pos < input.size() && (input[pos] == 'e' || input[pos] == 'E')) {
            ++pos;
            if (pos < input.size() && (input[pos] == '+' || input[pos] == '-')) ++pos;
            std::size_t exponent = pos;
            while (pos < input.size() && input[pos] >= '0' && input[pos] <= '9') ++pos;
            if (pos == exponent) throw std::runtime_error("malformed exponent");
        }
        std::size_t consumed = 0;
        double value = std::stod(input.substr(start, pos - start), &consumed);
        if (consumed != pos - start) throw std::runtime_error("invalid number");
        return checked(value);
    }

public:
    explicit Parser(const std::string& text) : input(text) {}

    double parse() {
        double value = expression();
        skipSpace();
        if (pos != input.size()) throw std::runtime_error("unexpected token");
        return value;
    }
};

int main(int argc, char** argv) {
    try {
        if (argc != 2) throw std::runtime_error("expected exactly one expression");
        std::cout << std::setprecision(17) << Parser(argv[1]).parse() << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "error: " << error.what() << '\n';
        return 1;
    }
}
