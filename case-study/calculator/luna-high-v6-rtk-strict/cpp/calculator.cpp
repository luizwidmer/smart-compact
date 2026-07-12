#include <cmath>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>

class Parser {
    const std::string& text;
    std::size_t pos = 0;

    static bool is_space(char c) {
        return c == ' ' || c == '\t' || c == '\n' || c == '\r' || c == '\v' || c == '\f';
    }

    void skip_space() {
        while (pos < text.size() && is_space(text[pos])) ++pos;
    }

    static double checked(double value) {
        if (!std::isfinite(value)) throw std::runtime_error("non-finite result");
        return value;
    }

    double parse_additive() {
        double value = parse_multiplicative();
        while (true) {
            skip_space();
            if (pos == text.size() || (text[pos] != '+' && text[pos] != '-')) return value;
            char op = text[pos++];
            double right = parse_multiplicative();
            value = checked(op == '+' ? value + right : value - right);
        }
    }

    double parse_multiplicative() {
        double value = parse_unary();
        while (true) {
            skip_space();
            if (pos == text.size() || (text[pos] != '*' && text[pos] != '/' && text[pos] != '%')) return value;
            char op = text[pos++];
            double right = parse_unary();
            if (right == 0.0) throw std::runtime_error("division by zero");
            if (op == '*') value = checked(value * right);
            else if (op == '/') value = checked(value / right);
            else value = checked(std::fmod(value, right));
        }
    }

    double parse_unary() {
        skip_space();
        if (pos < text.size() && (text[pos] == '+' || text[pos] == '-')) {
            char op = text[pos++];
            double value = parse_unary();
            return checked(op == '+' ? value : -value);
        }
        return parse_power();
    }

    double parse_power() {
        double value = parse_primary();
        skip_space();
        if (pos < text.size() && text[pos] == '^') {
            ++pos;
            return checked(std::pow(value, parse_unary()));
        }
        return value;
    }

    double parse_primary() {
        skip_space();
        if (pos == text.size()) throw std::runtime_error("expected expression");
        if (text[pos] == '(') {
            ++pos;
            double value = parse_additive();
            skip_space();
            if (pos == text.size() || text[pos] != ')') throw std::runtime_error("expected closing parenthesis");
            ++pos;
            return value;
        }
        return parse_number();
    }

    double parse_number() {
        std::size_t start = pos;
        std::size_t digits = 0;
        while (pos < text.size() && text[pos] >= '0' && text[pos] <= '9') { ++pos; ++digits; }
        if (pos < text.size() && text[pos] == '.') {
            ++pos;
            while (pos < text.size() && text[pos] >= '0' && text[pos] <= '9') { ++pos; ++digits; }
        }
        if (digits == 0) throw std::runtime_error("expected number");
        if (pos < text.size() && (text[pos] == 'e' || text[pos] == 'E')) {
            ++pos;
            if (pos < text.size() && (text[pos] == '+' || text[pos] == '-')) ++pos;
            std::size_t exponent_start = pos;
            while (pos < text.size() && text[pos] >= '0' && text[pos] <= '9') ++pos;
            if (pos == exponent_start) throw std::runtime_error("invalid exponent");
        }
        try {
            std::size_t used = 0;
            double value = std::stod(text.substr(start, pos - start), &used);
            if (used != pos - start) throw std::runtime_error("invalid number");
            return checked(value);
        } catch (const std::invalid_argument&) {
            throw std::runtime_error("invalid number");
        } catch (const std::out_of_range&) {
            throw std::runtime_error("non-finite result");
        }
    }

public:
    explicit Parser(const std::string& input) : text(input) {}

    double parse() {
        double value = parse_additive();
        skip_space();
        if (pos != text.size()) throw std::runtime_error("trailing tokens");
        return checked(value);
    }
};

int main(int argc, char** argv) {
    try {
        if (argc != 2) throw std::runtime_error("expected exactly one argument");
        double result = Parser(argv[1]).parse();
        std::cout << std::setprecision(17) << result << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "error: " << error.what() << '\n';
        return 1;
    }
}
