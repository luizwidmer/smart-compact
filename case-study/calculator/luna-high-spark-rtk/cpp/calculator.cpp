#include <cmath>
#include <cctype>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <string>

using namespace std;

namespace {

void fail(const string& message) {
    cerr << "error: " << message << "\n";
    exit(1);
}

class Parser {
public:
    explicit Parser(string text)
        : input_(move(text)), pos_(0), length_(input_.size()) {}

    double parse() {
        double value = parse_add_sub();
        skip_ws();
        if (pos_ != length_) {
            fail("trailing input");
        }
        return ensure_finite(value);
    }

private:
    string input_;
    size_t pos_;
    size_t length_;

    void skip_ws() {
        while (pos_ < length_ && isspace(static_cast<unsigned char>(input_[pos_]))) {
            ++pos_;
        }
    }

    double parse_add_sub() {
        double value = parse_mul_div_mod();
        while (true) {
            skip_ws();
            if (pos_ >= length_) {
                break;
            }
            char ch = input_[pos_];
            if (ch == '+') {
                ++pos_;
                double right = parse_mul_div_mod();
                value = ensure_finite(value + right);
            } else if (ch == '-') {
                ++pos_;
                double right = parse_mul_div_mod();
                value = ensure_finite(value - right);
            } else {
                break;
            }
        }
        return value;
    }

    double parse_mul_div_mod() {
        double value = parse_unary();
        while (true) {
            skip_ws();
            if (pos_ >= length_) {
                break;
            }
            char ch = input_[pos_];
            if (ch == '*') {
                ++pos_;
                double right = parse_unary();
                value = ensure_finite(value * right);
            } else if (ch == '/') {
                ++pos_;
                double right = parse_unary();
                if (right == 0.0) {
                    fail("division by zero");
                }
                value = ensure_finite(value / right);
            } else if (ch == '%') {
                ++pos_;
                double right = parse_unary();
                if (right == 0.0) {
                    fail("remainder by zero");
                }
                value = ensure_finite(fmod(value, right));
            } else {
                break;
            }
        }
        return value;
    }

    double parse_unary() {
        skip_ws();
        if (pos_ >= length_) {
            fail("malformed expression");
        }
        char ch = input_[pos_];
        if (ch == '+') {
            ++pos_;
            return parse_unary();
        }
        if (ch == '-') {
            ++pos_;
            return ensure_finite(-parse_unary());
        }
        return parse_pow();
    }

    double parse_pow() {
        double value = parse_primary();
        skip_ws();
        if (pos_ < length_ && input_[pos_] == '^') {
            ++pos_;
            double right = parse_pow();
            value = ensure_finite(pow(value, right));
        }
        return value;
    }

    double parse_primary() {
        skip_ws();
        if (pos_ >= length_) {
            fail("malformed expression");
        }
        if (input_[pos_] == '(') {
            ++pos_;
            double value = parse_add_sub();
            skip_ws();
            if (pos_ >= length_ || input_[pos_] != ')') {
                fail("missing closing parenthesis");
            }
            ++pos_;
            return value;
        }
        return parse_number();
    }

    double parse_number() {
        skip_ws();
        if (pos_ >= length_) {
            fail("malformed expression");
        }

        size_t start = pos_;
        bool has_exp = false;
        bool has_dot = false;
        bool has_digit = false;
        size_t exp_digits = 0;

        char first = input_[pos_];
        if (!(isdigit(static_cast<unsigned char>(first)) || first == '.')) {
            fail("invalid token");
        }

        if (first == '.') {
            ++pos_;
        }

        while (pos_ < length_) {
            char ch = input_[pos_];
            if (isdigit(static_cast<unsigned char>(ch))) {
                ++pos_;
                has_digit = true;
                if (has_exp) {
                    ++exp_digits;
                }
                continue;
            }
            if (ch == '.' && !has_dot && !has_exp) {
                ++pos_;
                has_dot = true;
                continue;
            }
            if ((ch == 'e' || ch == 'E') && !has_exp) {
                if (!has_digit && !has_dot) {
                    fail("invalid number");
                }
                ++pos_;
                has_exp = true;
                has_digit = false;
                if (pos_ < length_ && (input_[pos_] == '+' || input_[pos_] == '-')) {
                    ++pos_;
                }
                size_t exp_start = pos_;
                while (pos_ < length_ && isdigit(static_cast<unsigned char>(input_[pos_]))) {
                    ++pos_;
                    ++exp_digits;
                }
                if (exp_start == pos_) {
                    fail("invalid number");
                }
                break;
            }
            break;
        }

        if (pos_ == start) {
            fail("invalid number");
        }

        string token = input_.substr(start, pos_ - start);
        char* end = nullptr;
        double value = strtod(token.c_str(), &end);
        if (end != token.c_str() + token.size()) {
            fail("invalid number");
        }
        return ensure_finite(value);
    }

    static double ensure_finite(double value) {
        if (!isfinite(value)) {
            fail("non-finite result");
        }
        return value;
    }
};

} // namespace

int main(int argc, char* argv[]) {
    if (argc != 2) {
        fail("expected exactly one argument");
    }

    Parser parser(argv[1]);
    double result = parser.parse();
    cout << setprecision(17) << result << "\n";
    return 0;
}
