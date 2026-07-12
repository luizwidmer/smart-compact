#include <cmath>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <string>

class ParseError {};

class Parser {
public:
    explicit Parser(const std::string& input) : input_(input) {}

    double parse() {
        double value = expression();
        skip_space();
        if (pos_ != input_.size()) throw ParseError{};
        return checked(value);
    }

private:
    const std::string& input_;
    std::size_t pos_ = 0;

    void skip_space() {
        while (pos_ < input_.size() && (input_[pos_] == ' ' || input_[pos_] == '\t' || input_[pos_] == '\n' ||
                                        input_[pos_] == '\r' || input_[pos_] == '\v' || input_[pos_] == '\f')) ++pos_;
    }

    bool take(char token) {
        skip_space();
        if (pos_ < input_.size() && input_[pos_] == token) { ++pos_; return true; }
        return false;
    }

    double expression() {
        double value = term();
        for (;;) {
            if (take('+')) value = checked(value + term());
            else if (take('-')) value = checked(value - term());
            else return value;
        }
    }

    double term() {
        double value = unary();
        for (;;) {
            if (take('*')) value = checked(value * unary());
            else if (take('/')) {
                double right = unary();
                if (right == 0.0) throw ParseError{};
                value = checked(value / right);
            } else if (take('%')) {
                double right = unary();
                if (right == 0.0) throw ParseError{};
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
            double value = expression();
            if (!take(')')) throw ParseError{};
            return value;
        }

        skip_space();
        const std::size_t start = pos_;
        while (pos_ < input_.size() && input_[pos_] >= '0' && input_[pos_] <= '9') ++pos_;
        if (pos_ < input_.size() && input_[pos_] == '.') {
            ++pos_;
            while (pos_ < input_.size() && input_[pos_] >= '0' && input_[pos_] <= '9') ++pos_;
        } else if (pos_ == start && pos_ < input_.size() && input_[pos_] == '.') {
            ++pos_;
            const std::size_t fraction_start = pos_;
            while (pos_ < input_.size() && input_[pos_] >= '0' && input_[pos_] <= '9') ++pos_;
            if (pos_ == fraction_start) throw ParseError{};
        }
        if (pos_ == start) throw ParseError{};
        if (pos_ < input_.size() && (input_[pos_] == 'e' || input_[pos_] == 'E')) {
            ++pos_;
            if (pos_ < input_.size() && (input_[pos_] == '+' || input_[pos_] == '-')) ++pos_;
            const std::size_t exponent_start = pos_;
            while (pos_ < input_.size() && input_[pos_] >= '0' && input_[pos_] <= '9') ++pos_;
            if (pos_ == exponent_start) throw ParseError{};
        }
        char* end = nullptr;
        const std::string token = input_.substr(start, pos_ - start);
        const double value = std::strtod(token.c_str(), &end);
        if (end != token.c_str() + token.size()) throw ParseError{};
        return checked(value);
    }

    static double checked(double value) {
        if (!std::isfinite(value)) throw ParseError{};
        return value;
    }
};

int main(int argc, char** argv) {
    if (argc != 2) {
        std::cerr << "error: expected exactly one expression argument\n";
        return 2;
    }
    try {
        std::cout << std::setprecision(17) << Parser(argv[1]).parse() << '\n';
        return 0;
    } catch (const ParseError&) {
        std::cerr << "error: invalid expression\n";
        return 1;
    }
}
