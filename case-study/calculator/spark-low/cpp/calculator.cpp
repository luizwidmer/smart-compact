#include <cmath>
#include <iomanip>
#include <iostream>
#include <string>

class Parser {
public:
    Parser(const std::string &expr) : s(expr), i(0) {}

    double parseExpression() {
        double value = parseTerm();
        while (true) {
            skipWs();
            if (i >= s.size()) return value;
            char ch = s[i];
            if (ch != '+' && ch != '-') return value;
            ++i;
            double rhs = parseTerm();
            if (ch == '+') value += rhs;
            else value -= rhs;
        }
    }

    bool done() {
        skipWs();
        return i >= s.size();
    }

private:
    const std::string s;
    size_t i;

    void skipWs() {
        while (i < s.size() && std::isspace(static_cast<unsigned char>(s[i]))) ++i;
    }

    double parseNumber() {
        skipWs();
        size_t start = i;
        bool hasDigit = false;

        if (i < s.size() && s[i] == '.') {
            ++i;
            while (i < s.size() && std::isdigit(static_cast<unsigned char>(s[i]))) {
                ++i;
                hasDigit = true;
            }
        } else {
            while (i < s.size() && std::isdigit(static_cast<unsigned char>(s[i]))) {
                ++i;
                hasDigit = true;
            }
            if (i < s.size() && s[i] == '.') {
                ++i;
                while (i < s.size() && std::isdigit(static_cast<unsigned char>(s[i]))) {
                    ++i;
                    hasDigit = true;
                }
            }
        }

        if (!hasDigit) throw std::runtime_error("invalid number");

        if (i < s.size() && (s[i] == 'e' || s[i] == 'E')) {
            ++i;
            if (i < s.size() && (s[i] == '+' || s[i] == '-')) ++i;
            if (i >= s.size() || !std::isdigit(static_cast<unsigned char>(s[i]))) {
                throw std::runtime_error("invalid exponent");
            }
            while (i < s.size() && std::isdigit(static_cast<unsigned char>(s[i]))) ++i;
        }

        double value = std::stod(s.substr(start, i - start));
        if (!std::isfinite(value)) throw std::runtime_error("non-finite number");
        return value;
    }

    double parseUnary() {
        skipWs();
        if (i >= s.size()) throw std::runtime_error("unexpected end");
        if (s[i] == '+' || s[i] == '-') {
            char op = s[i++];
            double value = parseUnary();
            return op == '-' ? -value : value;
        }
        return parsePrimary();
    }

    double parsePrimary() {
        skipWs();
        if (i >= s.size()) throw std::runtime_error("unexpected end");
        if (s[i] == '(') {
            ++i;
            double value = parseExpression();
            skipWs();
            if (i >= s.size() || s[i] != ')') throw std::runtime_error("missing )");
            ++i;
            return value;
        }
        return parseNumber();
    }

    double parsePower() {
        double left = parseUnary();
        skipWs();
        if (i >= s.size() || s[i] != '^') return left;
        ++i;
        double right = parsePower();
        double value = std::pow(left, right);
        if (!std::isfinite(value)) throw std::runtime_error("non-finite result");
        return value;
    }

    double parseTerm() {
        double value = parsePower();
        while (true) {
            skipWs();
            if (i >= s.size()) return value;
            char ch = s[i];
            if (ch != '*' && ch != '/' && ch != '%') return value;
            ++i;
            double rhs = parsePower();
            if (ch == '*') value *= rhs;
            else if (ch == '/') {
                if (rhs == 0.0) throw std::runtime_error("division by zero");
                value /= rhs;
            } else {
                if (rhs == 0.0) throw std::runtime_error("remainder by zero");
                value = std::fmod(value, rhs);
            }
            if (!std::isfinite(value)) throw std::runtime_error("non-finite result");
        }
    }
};

int main(int argc, char **argv) {
    if (argc != 2) {
        std::cerr << "error: expected exactly one expression\n";
        return 1;
    }

    try {
        Parser parser(argv[1]);
        double value = parser.parseExpression();
        if (!parser.done()) throw std::runtime_error("trailing token");
        if (!std::isfinite(value)) throw std::runtime_error("non-finite result");
        std::cout.setf(std::ios::fmtflags(0), std::ios::floatfield);
        std::cout << std::setprecision(17) << value << "\n";
        return 0;
    } catch (const std::exception &e) {
        std::cerr << "error: " << e.what() << "\n";
        return 2;
    }
}
