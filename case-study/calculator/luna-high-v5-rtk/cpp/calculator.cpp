#include <cmath>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>

class CalcError : public std::runtime_error {
public:
    explicit CalcError(const std::string& message) : std::runtime_error(message) {}
};

class Parser {
    const std::string source;
    std::size_t pos = 0;

    static double checked(double value) {
        if (!std::isfinite(value)) throw CalcError("non-finite result");
        return value;
    }

    void skip_space() {
        while (pos < source.size() && (source[pos] == ' ' || source[pos] == '\t' || source[pos] == '\n' ||
               source[pos] == '\r' || source[pos] == '\v' || source[pos] == '\f')) ++pos;
    }

    bool take(char token) {
        skip_space();
        if (pos < source.size() && source[pos] == token) { ++pos; return true; }
        return false;
    }

    double parse_additive() {
        double value = parse_multiplicative();
        while (true) {
            if (take('+')) value = checked(value + parse_multiplicative());
            else if (take('-')) value = checked(value - parse_multiplicative());
            else return value;
        }
    }

    double parse_multiplicative() {
        double value = parse_unary();
        while (true) {
            if (take('*')) value = checked(value * parse_unary());
            else if (take('/')) {
                double rhs = parse_unary();
                if (rhs == 0.0) throw CalcError("division by zero");
                value = checked(value / rhs);
            } else if (take('%')) {
                double rhs = parse_unary();
                if (rhs == 0.0) throw CalcError("remainder by zero");
                value = checked(std::fmod(value, rhs));
            } else return value;
        }
    }

    double parse_unary() {
        if (take('+')) return parse_unary();
        if (take('-')) return checked(-parse_unary());
        return parse_power();
    }

    double parse_power() {
        double value = parse_primary();
        if (take('^')) return checked(std::pow(value, parse_unary()));
        return value;
    }

    double parse_primary() {
        skip_space();
        if (take('(')) {
            double value = parse_additive();
            if (!take(')')) throw CalcError("missing closing parenthesis");
            return value;
        }

        const std::size_t start = pos;
        std::size_t before = 0;
        while (pos < source.size() && source[pos] >= '0' && source[pos] <= '9') { ++pos; ++before; }
        std::size_t after = 0;
        if (pos < source.size() && source[pos] == '.') {
            ++pos;
            while (pos < source.size() && source[pos] >= '0' && source[pos] <= '9') { ++pos; ++after; }
        }
        if (before == 0 && after == 0) throw CalcError("expected number or parenthesis");
        if (pos < source.size() && (source[pos] == 'e' || source[pos] == 'E')) {
            ++pos;
            if (pos < source.size() && (source[pos] == '+' || source[pos] == '-')) ++pos;
            const std::size_t exponent_start = pos;
            while (pos < source.size() && source[pos] >= '0' && source[pos] <= '9') ++pos;
            if (pos == exponent_start) throw CalcError("invalid exponent");
        }

        const std::string token = source.substr(start, pos - start);
        char* end = nullptr;
        const double value = std::strtod(token.c_str(), &end);
        if (end != token.c_str() + token.size()) throw CalcError("invalid number");
        return checked(value);
    }

public:
    explicit Parser(std::string source) : source(std::move(source)) {}

    double parse() {
        double value = parse_additive();
        skip_space();
        if (pos != source.size()) throw CalcError("trailing tokens");
        return value;
    }
};

int main(int argc, char** argv) {
    if (argc != 2) { std::cerr << "error: expected exactly one expression\n"; return 1; }
    try {
        const double result = Parser(argv[1]).parse();
        std::cout << std::setprecision(17) << result << '\n';
        return 0;
    } catch (const CalcError& error) {
        std::cerr << "error: " << error.what() << '\n';
        return 1;
    }
}
