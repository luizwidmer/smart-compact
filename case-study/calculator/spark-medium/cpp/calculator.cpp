#include <cmath>
#include <iomanip>
#include <iostream>
#include <string>
#include <vector>

class Parser {
public:
    explicit Parser(std::string expr) : s(std::move(expr)), i(0), n(s.size()) {}

    bool parse(double &out, std::string &err) {
        if (!parse_expr(out, err)) return false;
        skip_ws();
        if (i != n) {
            err = "trailing tokens";
            return false;
        }
        if (!std::isfinite(out)) {
            err = "non-finite result";
            return false;
        }
        return true;
    }

private:
    bool parse_expr(double &out, std::string &err) { return parse_add(out, err); }

    bool parse_add(double &out, std::string &err) {
        if (!parse_mul(out, err)) return false;
        while (true) {
            skip_ws();
            if (match_char('+')) {
                double rhs;
                if (!parse_mul(rhs, err)) return false;
                out += rhs;
            } else if (match_char('-')) {
                double rhs;
                if (!parse_mul(rhs, err)) return false;
                out -= rhs;
            } else {
                break;
            }
            if (!std::isfinite(out)) { err = "non-finite result"; return false; }
        }
        return true;
    }

    bool parse_mul(double &out, std::string &err) {
        if (!parse_unary(out, err)) return false;
        while (true) {
            skip_ws();
            if (match_char('*')) {
                double rhs;
                if (!parse_unary(rhs, err)) return false;
                out *= rhs;
            } else if (match_char('/')) {
                double rhs;
                if (!parse_unary(rhs, err)) return false;
                if (rhs == 0.0) { err = "division by zero"; return false; }
                out /= rhs;
            } else if (match_char('%')) {
                double rhs;
                if (!parse_unary(rhs, err)) return false;
                if (rhs == 0.0) { err = "remainder by zero"; return false; }
                out = std::fmod(out, rhs);
            } else {
                break;
            }
            if (!std::isfinite(out)) { err = "non-finite result"; return false; }
        }
        return true;
    }

    bool parse_unary(double &out, std::string &err) {
        skip_ws();
        if (match_char('+')) return parse_unary(out, err);
        if (match_char('-')) {
            if (!parse_unary(out, err)) return false;
            out = -out;
            return true;
        }
        return parse_pow(out, err);
    }

    bool parse_pow(double &out, std::string &err) {
        if (!parse_primary(out, err)) return false;
        skip_ws();
        if (match_char('^')) {
            double rhs;
            if (!parse_pow(rhs, err)) return false;
            out = std::pow(out, rhs);
            if (!std::isfinite(out)) { err = "non-finite result"; return false; }
            return true;
        }
        return true;
    }

    bool parse_primary(double &out, std::string &err) {
        skip_ws();
        if (match_char('(')) {
            if (!parse_expr(out, err)) return false;
            skip_ws();
            if (!match_char(')')) { err = "missing closing parenthesis"; return false; }
            skip_ws();
            return true;
        }
        return parse_number(out, err);
    }

    bool parse_number(double &out, std::string &err) {
        skip_ws();
        size_t start = i;
        bool saw_digit = false;
        bool saw_dot = false;

        while (i < n && isdigit(s[i])) { i++; saw_digit = true; }
        if (i < n && s[i] == '.') {
            saw_dot = true;
            i++;
            while (i < n && isdigit(s[i])) { i++; saw_digit = true; }
        }
        if (!saw_digit && !saw_dot) { err = "expected number"; return false; }

        if (i < n && (s[i] == 'e' || s[i] == 'E')) {
            i++;
            if (i < n && (s[i] == '+' || s[i] == '-')) i++;
            if (i >= n || !isdigit(s[i])) { err = "invalid exponent"; return false; }
            while (i < n && isdigit(s[i])) i++;
        }

        try {
            out = std::stod(s.substr(start, i - start));
        } catch (...) {
            err = "invalid number";
            return false;
        }
        if (!std::isfinite(out)) { err = "non-finite literal"; return false; }
        return true;
    }

    void skip_ws() {
        while (i < n && isspace(static_cast<unsigned char>(s[i]))) i++;
    }

    bool match_char(char ch) {
        if (i < n && s[i] == ch) { i++; return true; }
        return false;
    }

    std::string s;
    size_t i;
    size_t n;
};

int main(int argc, char *argv[]) {
    if (argc != 2) {
        std::cerr << "error: expected exactly one expression argument" << '\n';
        return 1;
    }

    Parser parser(argv[1]);
    double result;
    std::string err;
    if (!parser.parse(result, err)) {
        std::cerr << "error: " << err << '\n';
        return 1;
    }

    if (result == -0.0) result = 0.0;
    std::cout << std::setprecision(17) << result << '\n';
    return 0;
}
