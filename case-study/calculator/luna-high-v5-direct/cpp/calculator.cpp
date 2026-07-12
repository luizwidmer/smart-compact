#include <cctype>
#include <cmath>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>

class ParseError : public std::runtime_error {
public:
    using std::runtime_error::runtime_error;
};

class Parser {
public:
    explicit Parser(const std::string& source) : source_(source) {}

    double parse() {
        double result = parse_additive();
        skip_space();
        if (position_ != source_.size()) throw ParseError("trailing tokens");
        return result;
    }

private:
    const std::string& source_;
    std::size_t position_ = 0;

    static double checked(double value) {
        if (!std::isfinite(value)) throw ParseError("non-finite result");
        return value;
    }

    void skip_space() {
        while (position_ < source_.size() && static_cast<unsigned char>(source_[position_]) < 128 && std::isspace(static_cast<unsigned char>(source_[position_]))) ++position_;
    }

    bool take(char character) {
        skip_space();
        if (position_ < source_.size() && source_[position_] == character) { ++position_; return true; }
        return false;
    }

    double parse_additive() {
        double result = parse_multiplicative();
        while (true) {
            if (take('+')) result = checked(result + parse_multiplicative());
            else if (take('-')) result = checked(result - parse_multiplicative());
            else return result;
        }
    }

    double parse_multiplicative() {
        double result = parse_unary();
        while (true) {
            if (take('*')) result = checked(result * parse_unary());
            else if (take('/')) {
                double right = parse_unary();
                if (right == 0.0) throw ParseError("division by zero");
                result = checked(result / right);
            } else if (take('%')) {
                double right = parse_unary();
                if (right == 0.0) throw ParseError("remainder by zero");
                result = checked(std::fmod(result, right));
            } else return result;
        }
    }

    double parse_unary() {
        if (take('+')) return parse_unary();
        if (take('-')) return checked(-parse_unary());
        return parse_power();
    }

    double parse_power() {
        double result = parse_primary();
        if (take('^')) return checked(std::pow(result, parse_unary()));
        return result;
    }

    double parse_primary() {
        if (take('(')) {
            double result = parse_additive();
            if (!take(')')) throw ParseError("expected ')'");
            return result;
        }

        skip_space();
        std::size_t start = position_;
        while (position_ < source_.size() && std::isdigit(static_cast<unsigned char>(source_[position_]))) ++position_;
        if (position_ < source_.size() && source_[position_] == '.') {
            ++position_;
            while (position_ < source_.size() && std::isdigit(static_cast<unsigned char>(source_[position_]))) ++position_;
        } else if (start == position_ && position_ < source_.size() && source_[position_] == '.') {
            ++position_;
            std::size_t fraction_start = position_;
            while (position_ < source_.size() && std::isdigit(static_cast<unsigned char>(source_[position_]))) ++position_;
            if (fraction_start == position_) throw ParseError("expected number or '('");
        }
        if (start == position_) throw ParseError("expected number or '('");
        if (position_ < source_.size() && (source_[position_] == 'e' || source_[position_] == 'E')) {
            ++position_;
            if (position_ < source_.size() && (source_[position_] == '+' || source_[position_] == '-')) ++position_;
            std::size_t exponent_start = position_;
            while (position_ < source_.size() && std::isdigit(static_cast<unsigned char>(source_[position_]))) ++position_;
            if (exponent_start == position_) throw ParseError("invalid exponent");
        }
        double result = std::strtod(source_.c_str() + start, nullptr);
        return checked(result);
    }
};

int main(int argc, char** argv) {
    if (argc != 2) { std::cerr << "error: expected exactly one expression\n"; return 1; }
    try {
        double result = Parser(argv[1]).parse();
        std::cout << std::setprecision(std::numeric_limits<double>::max_digits10) << result << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "error: " << error.what() << '\n';
        return 1;
    }
}
