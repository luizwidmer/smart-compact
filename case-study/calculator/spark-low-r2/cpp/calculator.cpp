#include <cmath>
#include <cstdlib>
#include <iostream>
#include <iomanip>
#include <string>

class Parser {
public:
    explicit Parser(const std::string &s) : text(s), i(0), n(s.size()) {}

    double parse() {
        double v = parseExpr();
        skipWs();
        if (i != n) error("unexpected token");
        if (!std::isfinite(v)) error("non-finite result");
        return v;
    }

private:
    std::string text;
    size_t i;
    size_t n;

    void error(const std::string &msg) {
        std::cerr << "error: " << msg << "\n";
        std::exit(1);
    }

    void skipWs() {
        while (i < n && std::isspace(static_cast<unsigned char>(text[i]))) ++i;
    }

    double parseExpr() {
        double v = parseTerm();
        while (true) {
            skipWs();
            if (i >= n) break;
            char op = text[i];
            if (op != '+' && op != '-') break;
            ++i;
            double rhs = parseTerm();
            v = (op == '+') ? (v + rhs) : (v - rhs);
            if (!std::isfinite(v)) error("non-finite result");
        }
        return v;
    }

    double parseTerm() {
        double v = parseUnary();
        while (true) {
            skipWs();
            if (i >= n) break;
            char op = text[i];
            if (op != '*' && op != '/' && op != '%') break;
            ++i;
            double rhs = parseUnary();
            if (op == '*') {
                v *= rhs;
            } else if (op == '/') {
                if (rhs == 0.0) error("division by zero");
                v /= rhs;
            } else {
                if (rhs == 0.0) error("remainder by zero");
                v = std::fmod(v, rhs);
            }
            if (!std::isfinite(v)) error("non-finite result");
        }
        return v;
    }

    double parseUnary() {
        skipWs();
        if (i >= n) error("unexpected end of input");
        if (text[i] == '+') {
            ++i;
            return parseUnary();
        }
        if (text[i] == '-') {
            ++i;
            return -parseUnary();
        }
        return parsePower();
    }

    double parsePower() {
        double v = parsePrimary();
        skipWs();
        if (i < n && text[i] == '^') {
            ++i;
            double rhs = parseUnary();
            v = std::pow(v, rhs);
            if (!std::isfinite(v)) error("non-finite result");
        }
        return v;
    }

    double parseNumber() {
        size_t start = i;
        bool hasDigit = false;

        if (i >= n) return std::numeric_limits<double>::quiet_NaN();

        if (text[i] == '.') {
            ++i;
            if (i < n && std::isdigit(static_cast<unsigned char>(text[i]))) {
                hasDigit = true;
                while (i < n && std::isdigit(static_cast<unsigned char>(text[i]))) ++i;
            } else {
                return std::numeric_limits<double>::quiet_NaN();
            }
        } else if (std::isdigit(static_cast<unsigned char>(text[i]))) {
            while (i < n && std::isdigit(static_cast<unsigned char>(text[i]))) {
                ++i;
                hasDigit = true;
            }
            if (i < n && text[i] == '.') {
                ++i;
                while (i < n && std::isdigit(static_cast<unsigned char>(text[i]))) ++i;
            }
        } else {
            return std::numeric_limits<double>::quiet_NaN();
        }

        if (i < n && (text[i] == 'e' || text[i] == 'E')) {
            ++i;
            if (i < n && (text[i] == '+' || text[i] == '-')) ++i;
            if (i >= n || !std::isdigit(static_cast<unsigned char>(text[i]))) {
                return std::numeric_limits<double>::quiet_NaN();
            }
            while (i < n && std::isdigit(static_cast<unsigned char>(text[i]))) ++i;
        }

        if (!hasDigit) return std::numeric_limits<double>::quiet_NaN();

        try {
            return std::stod(text.substr(start, i - start));
        } catch (...) {
            return std::numeric_limits<double>::quiet_NaN();
        }
    }

    double parsePrimary() {
        skipWs();
        if (i >= n) error("unexpected end of input");
        if (text[i] == '(') {
            ++i;
            double v = parseExpr();
            skipWs();
            if (i >= n || text[i] != ')') error("missing closing parenthesis");
            ++i;
            return v;
        }
        double v = parseNumber();
        if (!std::isfinite(v) && std::isnan(v)) error("invalid number");
        return v;
    }
};

int main(int argc, char *argv[]) {
    if (argc != 2) {
        std::cerr << "error: usage: calculator <expression>\n";
        return 1;
    }

    Parser p(argv[1]);
    double v = p.parse();
    if (!std::isfinite(v)) {
        std::cerr << "error: non-finite result\n";
        return 1;
    }

    if (v == std::trunc(v)) {
        std::cout << static_cast<long long>(v) << "\n";
    } else {
        std::cout << std::setprecision(17) << v << "\n";
    }

    return 0;
}
