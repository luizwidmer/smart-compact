#include <cmath>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <string>

class Parser {
 public:
  explicit Parser(std::string text) : text_(std::move(text)) {}

  double parse() {
    double value = parse_expression();
    skip_whitespace();
    if (pos_ != text_.size()) fail("trailing tokens");
    return value;
  }

 private:
  std::string text_;
  std::size_t pos_ = 0;

  [[noreturn]] void fail(const std::string& message) const {
    throw std::runtime_error(message);
  }

  void skip_whitespace() {
    while (pos_ < text_.size()) {
      const char c = text_[pos_];
      if (c == ' ' || c == '\t' || c == '\n' || c == '\r' || c == '\v' || c == '\f') ++pos_;
      else break;
    }
  }

  bool match(char token) {
    skip_whitespace();
    if (pos_ < text_.size() && text_[pos_] == token) {
      ++pos_;
      return true;
    }
    return false;
  }

  double parse_number() {
    skip_whitespace();
    const std::size_t start = pos_;
    std::size_t digits = 0;
    while (pos_ < text_.size() && text_[pos_] >= '0' && text_[pos_] <= '9') { ++pos_; ++digits; }
    if (pos_ < text_.size() && text_[pos_] == '.') {
      ++pos_;
      while (pos_ < text_.size() && text_[pos_] >= '0' && text_[pos_] <= '9') { ++pos_; ++digits; }
    }
    if (digits == 0) fail("expected number");
    if (pos_ < text_.size() && (text_[pos_] == 'e' || text_[pos_] == 'E')) {
      ++pos_;
      if (pos_ < text_.size() && (text_[pos_] == '+' || text_[pos_] == '-')) ++pos_;
      const std::size_t exponent_start = pos_;
      while (pos_ < text_.size() && text_[pos_] >= '0' && text_[pos_] <= '9') ++pos_;
      if (exponent_start == pos_) fail("invalid exponent");
    }
    const double value = std::stod(text_.substr(start, pos_ - start));
    if (!std::isfinite(value)) fail("non-finite number");
    return value;
  }

  double parse_primary() {
    if (match('(')) {
      const double value = parse_expression();
      if (!match(')')) fail("expected ')' ");
      return value;
    }
    return parse_number();
  }

  double parse_power() {
    const double value = parse_primary();
    if (match('^')) {
      const double result = std::pow(value, parse_unary());
      if (!std::isfinite(result)) fail("non-finite result");
      return result;
    }
    return value;
  }

  double parse_unary() {
    if (match('+')) return parse_unary();
    if (match('-')) {
      const double result = -parse_unary();
      if (!std::isfinite(result)) fail("non-finite result");
      return result;
    }
    return parse_power();
  }

  double parse_multiplicative() {
    double value = parse_unary();
    while (true) {
      if (match('*')) value *= parse_unary();
      else if (match('/')) {
        const double divisor = parse_unary();
        if (divisor == 0.0) fail("division by zero");
        value /= divisor;
      } else if (match('%')) {
        const double divisor = parse_unary();
        if (divisor == 0.0) fail("remainder by zero");
        value = std::fmod(value, divisor);
      } else break;
      if (!std::isfinite(value)) fail("non-finite result");
    }
    return value;
  }

  double parse_expression() {
    double value = parse_multiplicative();
    while (true) {
      if (match('+')) value += parse_multiplicative();
      else if (match('-')) value -= parse_multiplicative();
      else break;
      if (!std::isfinite(value)) fail("non-finite result");
    }
    return value;
  }
};

int main(int argc, char** argv) {
  if (argc != 2) {
    std::cerr << "error: expected exactly one expression argument\n";
    return 1;
  }
  try {
    std::cout << std::setprecision(17) << Parser(argv[1]).parse() << '\n';
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "error: " << error.what() << '\n';
    return 1;
  }
}
