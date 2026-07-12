/*
 * SPDX-License-Identifier: Apache-2.0
 */

#include <cmath>
#include <cctype>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>

class Parser {
  public:
    explicit Parser(std::string_view input) : input_(input), pos_(0) {}

    double parse() {
        double value = parse_expr();
        skip_ws();
        if (pos_ != input_.size()) {
            throw std::runtime_error("trailing input");
        }
        ensure_finite(value);
        return value;
    }

  private:
    std::string_view input_;
    size_t pos_;

    double parse_expr() {
        double left = parse_term();
        while (true) {
            skip_ws();
            if (consume('+')) {
                left = ensure_finite(left + parse_term());
            } else if (consume('-')) {
                left = ensure_finite(left - parse_term());
            } else {
                return left;
            }
        }
    }

    double parse_term() {
        double left = parse_pow();
        while (true) {
            skip_ws();
            if (consume('*')) {
                left = ensure_finite(left * parse_pow());
            } else if (consume('/')) {
                double rhs = parse_pow();
                if (rhs == 0.0) {
                    throw std::runtime_error("division by zero");
                }
                left = ensure_finite(left / rhs);
            } else if (consume('%')) {
                double rhs = parse_pow();
                if (rhs == 0.0) {
                    throw std::runtime_error("remainder by zero");
                }
                left = ensure_finite(std::fmod(left, rhs));
            } else {
                return left;
            }
        }
    }

    double parse_pow() {
        double left = parse_unary();
        skip_ws();
        if (consume('^')) {
            return ensure_finite(std::pow(left, parse_pow()));
        }
        return left;
    }

    double parse_unary() {
        skip_ws();
        if (consume('+')) {
            return parse_unary();
        }
        if (consume('-')) {
            return ensure_finite(-parse_unary());
        }
        return parse_primary();
    }

    double parse_primary() {
        skip_ws();
        if (consume('(')) {
            double value = parse_expr();
            skip_ws();
            if (!consume(')')) {
                throw std::runtime_error("missing ')'");
            }
            return value;
        }

        if (pos_ >= input_.size()) {
            throw std::runtime_error("unexpected end of input");
        }

        char ch = input_[pos_];
        if (std::isdigit(static_cast<unsigned char>(ch)) || ch == '.') {
            return parse_number();
        }
        throw std::runtime_error("unexpected token");
    }

    double parse_number() {
        skip_ws();
        if (pos_ >= input_.size()) {
            throw std::runtime_error("unexpected end of input");
        }
        if (input_[pos_] == '.') {
            if (pos_ + 1 >= input_.size() || !std::isdigit(static_cast<unsigned char>(input_[pos_ + 1]))) {
                throw std::runtime_error("invalid number");
            }
        } else if (!std::isdigit(static_cast<unsigned char>(input_[pos_]))) {
            throw std::runtime_error("invalid number");
        }

        size_t start = pos_;
        char *end = nullptr;
        double value = std::strtod(input_.data() + pos_, &end);
        if (end == input_.data() + pos_) {
            throw std::runtime_error("invalid number");
        }
        pos_ = static_cast<size_t>(end - input_.data());
        ensure_finite(value);
        return value;
    }

    void skip_ws() {
        while (pos_ < input_.size() && std::isspace(static_cast<unsigned char>(input_[pos_]))) {
            ++pos_;
        }
    }

    bool consume(char ch) {
        if (pos_ < input_.size() && input_[pos_] == ch) {
            ++pos_;
            return true;
        }
        return false;
    }

    static double ensure_finite(double value) {
        if (!std::isfinite(value)) {
            throw std::runtime_error("non-finite value");
        }
        return value;
    }
};

int main(int argc, char **argv) {
    if (argc != 2) {
        std::cerr << "error: expected exactly one expression argument\n";
        return 1;
    }

    try {
        Parser parser(argv[1]);
        double value = parser.parse();
        std::cout << std::setprecision(17) << value << '\n';
        return 0;
    } catch (const std::exception &ex) {
        std::cerr << "error: " << ex.what() << '\n';
        return 1;
    }
}
