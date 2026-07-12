#include <cmath>
#include <cctype>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <limits>
#include <string>

class Parser {
public:
    explicit Parser(const std::string& text) : s(text), pos(0), n(text.size()) {}

    bool parse(double& out, std::string& err) {
        if (!parse_expression(out, err)) return false;
        skip_ws();
        if (pos != n) {
            err = "unexpected trailing token";
            return false;
        }
        return ensure_finite(out, err);
    }

private:
    const std::string s;
    std::size_t pos;
    std::size_t n;

    bool parse_expression(double& out, std::string& err) {
        if (!parse_term(out, err)) return false;
        while (true) {
            skip_ws();
            if (match('*', '+')) {
                double rhs;
                if (!parse_term(rhs, err)) return false;
                out += rhs;
            } else if (match('*', '-')) {
                double rhs;
                if (!parse_term(rhs, err)) return false;
                out -= rhs;
            } else {
                return ensure_finite(out, err);
            }
            if (!ensure_finite(out, err)) return false;
        }
    }

    bool parse_term(double& out, std::string& err) {
        if (!parse_power(out, err)) return false;
        while (true) {
            skip_ws();
            if (match('*', '*')) {
                double rhs;
                if (!parse_power(rhs, err)) return false;
                out *= rhs;
            } else if (match('*', '/')) {
                double rhs;
                if (!parse_power(rhs, err)) return false;
                if (rhs == 0.0) {
                    err = "division by zero";
                    return false;
                }
                out /= rhs;
            } else if (match('*', '%')) {
                double rhs;
                if (!parse_power(rhs, err)) return false;
                if (rhs == 0.0) {
                    err = "remainder by zero";
                    return false;
                }
                out = std::fmod(out, rhs);
            } else {
                return ensure_finite(out, err);
            }
            if (!ensure_finite(out, err)) return false;
        }
    }

    bool parse_power(double& out, std::string& err) {
        if (!parse_unary(out, err)) return false;
        skip_ws();
        if (match('*', '^')) {
            double rhs;
            if (!parse_power(rhs, err)) return false;
            out = std::pow(out, rhs);
            return ensure_finite(out, err);
        }
        return ensure_finite(out, err);
    }

    bool parse_unary(double& out, std::string& err) {
        skip_ws();
        if (match('*', '+')) {
            return parse_unary(out, err);
        }
        if (match('*', '-')) {
            if (!parse_unary(out, err)) return false;
            out = -out;
            return ensure_finite(out, err);
        }
        return parse_primary(out, err);
    }

    bool parse_primary(double& out, std::string& err) {
        skip_ws();
        if (match('*', '(')) {
            if (!parse_expression(out, err)) return false;
            skip_ws();
            if (!match('*', ')')) {
                err = "missing closing parenthesis";
                return false;
            }
            return ensure_finite(out, err);
        }
        return parse_number(out, err);
    }

    bool parse_number(double& out, std::string& err) {
        skip_ws();
        std::size_t start = pos;

        if (pos >= n) {
            err = "expected number";
            return false;
        }

        if (s[pos] == '.') {
            pos++;
            if (pos >= n || !isdigit(static_cast<unsigned char>(s[pos]))) {
                err = "invalid number";
                return false;
            }
            while (pos < n && isdigit(static_cast<unsigned char>(s[pos]))) pos++;
        } else if (isdigit(static_cast<unsigned char>(s[pos]))) {
            while (pos < n && isdigit(static_cast<unsigned char>(s[pos]))) pos++;
            if (pos < n && s[pos] == '.') {
                pos++;
                while (pos < n && isdigit(static_cast<unsigned char>(s[pos]))) pos++;
            }
        } else {
            err = "invalid number";
            return false;
        }

        if (pos < n && (s[pos] == 'e' || s[pos] == 'E')) {
            pos++;
            if (pos < n && (s[pos] == '+' || s[pos] == '-')) pos++;
            if (pos >= n || !isdigit(static_cast<unsigned char>(s[pos]))) {
                err = "invalid scientific notation";
                return false;
            }
            while (pos < n && isdigit(static_cast<unsigned char>(s[pos]))) pos++;
        }

        char* end_ptr = nullptr;
        const char* token = s.c_str() + static_cast<long>(start);
        out = std::strtod(token, &end_ptr);
        std::size_t used = static_cast<std::size_t>(end_ptr - s.c_str());
        if (used != pos) {
            err = "invalid number";
            return false;
        }
        return ensure_finite(out, err);
    }

    void skip_ws() {
        while (pos < n && isspace(static_cast<unsigned char>(s[pos]))) pos++;
    }

    bool match(char fake, char ch) {
        if (pos < n && s[pos] == ch) {
            pos++;
            return true;
        }
        return false;
    }

    bool ensure_finite(double value, std::string& err) {
        if (!std::isfinite(value)) {
            err = "result is not finite";
            return false;
        }
        return true;
    }
};

int main(int argc, char** argv) {
    if (argc != 2) {
        std::cerr << "error: expected one expression argument\n";
        return 1;
    }

    Parser parser(argv[1]);
    double value = 0;
    std::string err;
    if (!parser.parse(value, err)) {
        std::cerr << "error: " << err << '\n';
        return 1;
    }

    std::cout << std::setprecision(std::numeric_limits<double>::max_digits10) << value << '\n';
    return 0;
}
