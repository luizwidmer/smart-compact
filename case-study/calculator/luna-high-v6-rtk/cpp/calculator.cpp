#include <cmath>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>

class Parser {
    const std::string& text;
    std::size_t pos = 0;

    void skip_space() {
        while (pos < text.size() && (text[pos] == ' ' || text[pos] == '\t' || text[pos] == '\n' || text[pos] == '\r' || text[pos] == '\v' || text[pos] == '\f')) ++pos;
    }
    bool take(char wanted) {
        skip_space();
        if (pos < text.size() && text[pos] == wanted) { ++pos; return true; }
        return false;
    }
    static double checked(double value) {
        if (!std::isfinite(value)) throw std::runtime_error("non-finite result");
        return value;
    }
public:
    explicit Parser(const std::string& input) : text(input) {}

    double parse() {
        double value = addition();
        skip_space();
        if (pos != text.size()) throw std::runtime_error("trailing token");
        return value;
    }
    double addition() {
        double value = multiplication();
        while (true) {
            if (take('+')) value = checked(value + multiplication());
            else if (take('-')) value = checked(value - multiplication());
            else return value;
        }
    }
    double multiplication() {
        double value = unary();
        while (true) {
            if (take('*')) value = checked(value * unary());
            else if (take('/')) {
                double right = unary();
                if (right == 0.0) throw std::runtime_error("division by zero");
                value = checked(value / right);
            } else if (take('%')) {
                double right = unary();
                if (right == 0.0) throw std::runtime_error("remainder by zero");
                value = checked(std::fmod(value, right));
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
        if (take('^')) return checked(std::pow(value, unary()));
        return value;
    }
    double primary() {
        if (take('(')) {
            double value = addition();
            if (!take(')')) throw std::runtime_error("missing closing parenthesis");
            return value;
        }
        skip_space();
        const std::size_t start = pos;
        std::size_t digits = 0;
        while (pos < text.size() && text[pos] >= '0' && text[pos] <= '9') { ++pos; ++digits; }
        if (pos < text.size() && text[pos] == '.') {
            ++pos;
            while (pos < text.size() && text[pos] >= '0' && text[pos] <= '9') ++pos;
        } else if (digits == 0) throw std::runtime_error("expected number or parenthesis");
        if (digits == 0 && pos == start + 1) throw std::runtime_error("expected digits");
        if (pos < text.size() && (text[pos] == 'e' || text[pos] == 'E')) {
            ++pos;
            if (pos < text.size() && (text[pos] == '+' || text[pos] == '-')) ++pos;
            const std::size_t exponent_start = pos;
            while (pos < text.size() && text[pos] >= '0' && text[pos] <= '9') ++pos;
            if (pos == exponent_start) throw std::runtime_error("invalid exponent");
        }
        try { return checked(std::stod(text.substr(start, pos - start))); }
        catch (const std::exception&) { throw std::runtime_error("invalid number"); }
    }
};

int main(int argc, char** argv) {
    if (argc != 2) { std::cerr << "error: expected exactly one expression\n"; return 2; }
    try {
        const double result = Parser(argv[1]).parse();
        std::cout << std::setprecision(17) << result << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "error: " << error.what() << '\n';
        return 1;
    }
}
