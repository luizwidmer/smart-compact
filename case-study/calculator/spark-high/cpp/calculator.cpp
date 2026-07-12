#include <cmath>
#include <cstddef>
#include <iostream>
#include <sstream>
#include <limits>
#include <string>

struct ParseError {
  const char *msg;
};

class Parser {
 public:
  explicit Parser(const std::string &expr) : expr_(expr), len_(expr.size()), pos_(0) {}

  double parse() {
    skip_ws();
    if (pos_ >= len_) {
      throw ParseError{"empty expression"};
    }
    double value = parse_add_sub();
    skip_ws();
    if (pos_ != len_) {
      throw ParseError{"unexpected token"};
    }
    if (!std::isfinite(value)) {
      throw ParseError{"non-finite result"};
    }
    return value;
  }

 private:
  std::string expr_;
  std::size_t len_;
  std::size_t pos_;

  double parse_add_sub() {
    double value = parse_mul_div();
    while (true) {
      skip_ws();
      if (consume('+')) {
        value += parse_mul_div();
      } else if (consume('-')) {
        value -= parse_mul_div();
      } else {
        break;
      }
    }
    return value;
  }

  double parse_mul_div() {
    double value = parse_unary();
    while (true) {
      skip_ws();
      if (consume('*')) {
        value *= parse_unary();
      } else if (consume('/')) {
        double rhs = parse_unary();
        if (rhs == 0.0) {
          throw ParseError{"division by zero"};
        }
        value /= rhs;
      } else if (consume('%')) {
        double rhs = parse_unary();
        if (rhs == 0.0) {
          throw ParseError{"remainder by zero"};
        }
        value = std::fmod(value, rhs);
      } else {
        break;
      }
    }
    return value;
  }

  double parse_unary() {
    skip_ws();
    if (consume('+')) {
      return parse_unary();
    }
    if (consume('-')) {
      return -parse_unary();
    }
    return parse_pow();
  }

  double parse_pow() {
    double value = parse_primary();
    skip_ws();
    if (consume('^')) {
      double right = parse_pow();
      value = std::pow(value, right);
    }
    return value;
  }

  double parse_primary() {
    skip_ws();
    if (consume('(')) {
      double value = parse_add_sub();
      skip_ws();
      if (!consume(')')) {
        throw ParseError{"missing closing parenthesis"};
      }
      return value;
    }
    return parse_number();
  }

  double parse_number() {
    std::size_t start = pos_;

    bool saw_digits_before = false;
    if (match_char('.')) {
      if (pos_ >= len_ || !std::isdigit(expr_[pos_])) {
        throw ParseError{"malformed number"};
      }
      while (pos_ < len_ && std::isdigit(expr_[pos_])) {
        pos_++;
      }
    } else {
      while (pos_ < len_ && std::isdigit(expr_[pos_])) {
        pos_++;
        saw_digits_before = true;
      }
      if (match_char('.')) {
        while (pos_ < len_ && std::isdigit(expr_[pos_])) {
          pos_++;
        }
      } else if (!saw_digits_before) {
        throw ParseError{"malformed number"};
      }
    }

    if (pos_ < len_ && (expr_[pos_] == 'e' || expr_[pos_] == 'E')) {
      pos_++;
      if (pos_ < len_ && (expr_[pos_] == '+' || expr_[pos_] == '-')) {
        pos_++;
      }
      if (pos_ >= len_ || !std::isdigit(expr_[pos_])) {
        throw ParseError{"malformed number"};
      }
      while (pos_ < len_ && std::isdigit(expr_[pos_])) {
        pos_++;
      }
    }

    double value = std::stod(expr_.substr(start, pos_ - start));
    if (!std::isfinite(value)) {
      throw ParseError{"non-finite number"};
    }
    return value;
  }

  void skip_ws() {
    while (pos_ < len_ && std::isspace(static_cast<unsigned char>(expr_[pos_]))) {
      pos_++;
    }
  }

  bool consume(char expected) {
    if (pos_ < len_ && expr_[pos_] == expected) {
      pos_++;
      return true;
    }
    return false;
  }

  bool match_char(char expected) {
    return consume(expected);
  }
};

bool is_integer(double value) {
  return std::fmod(value, 1.0) == 0.0;
}

int main(int argc, char **argv) {
  if (argc != 2) {
    std::cerr << "error: expected one expression argument" << std::endl;
    return 1;
  }

  try {
    Parser parser(argv[1]);
    double value = parser.parse();

    std::ostringstream out;
    if (is_integer(value)) {
      out.setf(std::ios::fixed);
      out.precision(0);
      out << value;
    } else {
      out.precision(std::numeric_limits<double>::max_digits10);
      out << value;
    }
    std::cout << out.str() << std::endl;
    return 0;
  } catch (ParseError &err) {
    std::cerr << "error: " << err.msg << std::endl;
    return 1;
  } catch (const std::exception &) {
    std::cerr << "error: parse error" << std::endl;
    return 1;
  }
}
