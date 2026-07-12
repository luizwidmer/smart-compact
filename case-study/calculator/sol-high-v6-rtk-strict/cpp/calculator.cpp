#include <cmath>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>

class Parser {
    std::string text; std::size_t pos = 0;
    void space() { while (pos < text.size() && (text[pos] == ' ' || text[pos] == '\t' || text[pos] == '\n' || text[pos] == '\r' || text[pos] == '\v' || text[pos] == '\f')) ++pos; }
    bool take(char ch) { space(); if (pos < text.size() && text[pos] == ch) { ++pos; return true; } return false; }
    static double checked(double value) { if (!std::isfinite(value)) throw std::runtime_error("non-finite value"); return value; }
    double expression() { double value = product(); for (;;) { if (take('+')) value = checked(value + product()); else if (take('-')) value = checked(value - product()); else return value; } }
    double product() {
        double value = unary();
        for (;;) {
            if (take('*')) value = checked(value * unary());
            else if (take('/')) { double rhs = unary(); if (rhs == 0) throw std::runtime_error("division by zero"); value = checked(value / rhs); }
            else if (take('%')) { double rhs = unary(); if (rhs == 0) throw std::runtime_error("remainder by zero"); value = checked(std::fmod(value, rhs)); }
            else return value;
        }
    }
    double unary() { if (take('+')) return unary(); if (take('-')) return checked(-unary()); return power(); }
    double power() { double value = primary(); if (take('^')) value = checked(std::pow(value, unary())); return value; }
    double primary() {
        if (take('(')) { double value = expression(); if (!take(')')) throw std::runtime_error("expected closing parenthesis"); return value; }
        space(); std::size_t start = pos; bool digits = false;
        while (pos < text.size() && text[pos] >= '0' && text[pos] <= '9') { ++pos; digits = true; }
        if (pos < text.size() && text[pos] == '.') { ++pos; while (pos < text.size() && text[pos] >= '0' && text[pos] <= '9') { ++pos; digits = true; } }
        if (!digits) throw std::runtime_error("expected number");
        if (pos < text.size() && (text[pos] == 'e' || text[pos] == 'E')) { ++pos; if (pos < text.size() && (text[pos] == '+' || text[pos] == '-')) ++pos; std::size_t exponent = pos; while (pos < text.size() && text[pos] >= '0' && text[pos] <= '9') ++pos; if (pos == exponent) throw std::runtime_error("malformed exponent"); }
        return checked(std::stod(text.substr(start, pos - start)));
    }
public:
    explicit Parser(std::string input) : text(std::move(input)) {}
    double parse() { double value = expression(); space(); if (pos != text.size()) throw std::runtime_error("trailing input"); return value; }
};

int main(int argc, char** argv) {
    try { if (argc != 2) throw std::runtime_error("expected exactly one expression"); std::cout << std::setprecision(17) << Parser(argv[1]).parse() << '\n'; return 0; }
    catch (const std::exception& error) { std::cerr << "error: " << error.what() << '\n'; return 1; }
}
