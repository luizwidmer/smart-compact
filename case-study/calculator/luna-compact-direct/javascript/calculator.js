"use strict";

class CalculatorError extends Error {}

class ExpressionParser {
  constructor(source) {
    this.source = source;
    this.index = 0;
  }

  skipWhitespace() {
    while (this.index < this.source.length && " \t\n\r\v\f".includes(this.source[this.index])) {
      this.index += 1;
    }
  }

  take(character) {
    this.skipWhitespace();
    if (this.index < this.source.length && this.source[this.index] === character) {
      this.index += 1;
      return true;
    }
    return false;
  }

  finite(value) {
    if (!Number.isFinite(value)) throw new CalculatorError("non-finite result");
    return value;
  }

  evaluate() {
    const result = this.parseSum();
    this.skipWhitespace();
    if (this.index !== this.source.length) throw new CalculatorError("unexpected trailing input");
    return result;
  }

  parseSum() {
    let result = this.parseProduct();
    while (true) {
      if (this.take("+")) result = this.finite(result + this.parseProduct());
      else if (this.take("-")) result = this.finite(result - this.parseProduct());
      else return result;
    }
  }

  parseProduct() {
    let result = this.parseUnary();
    while (true) {
      if (this.take("*")) {
        result = this.finite(result * this.parseUnary());
      } else if (this.take("/")) {
        const divisor = this.parseUnary();
        if (divisor === 0) throw new CalculatorError("division by zero");
        result = this.finite(result / divisor);
      } else if (this.take("%")) {
        const divisor = this.parseUnary();
        if (divisor === 0) throw new CalculatorError("remainder by zero");
        result = this.finite(result % divisor);
      } else {
        return result;
      }
    }
  }

  parseUnary() {
    if (this.take("+")) return this.parseUnary();
    if (this.take("-")) return this.finite(-this.parseUnary());
    return this.parsePower();
  }

  parsePower() {
    const base = this.parsePrimary();
    if (this.take("^")) return this.finite(Math.pow(base, this.parseUnary()));
    return base;
  }

  parsePrimary() {
    if (this.take("(")) {
      const result = this.parseSum();
      if (!this.take(")")) throw new CalculatorError("expected closing parenthesis");
      return result;
    }
    return this.parseNumber();
  }

  parseNumber() {
    this.skipWhitespace();
    const start = this.index;
    let digitCount = 0;

    while (this.index < this.source.length && this.source[this.index] >= "0" && this.source[this.index] <= "9") {
      this.index += 1;
      digitCount += 1;
    }
    if (this.index < this.source.length && this.source[this.index] === ".") {
      this.index += 1;
      while (this.index < this.source.length && this.source[this.index] >= "0" && this.source[this.index] <= "9") {
        this.index += 1;
        digitCount += 1;
      }
    }
    if (digitCount === 0) throw new CalculatorError("expected number");

    if (this.source[this.index] === "e" || this.source[this.index] === "E") {
      this.index += 1;
      if (this.source[this.index] === "+" || this.source[this.index] === "-") this.index += 1;
      const exponentStart = this.index;
      while (this.index < this.source.length && this.source[this.index] >= "0" && this.source[this.index] <= "9") {
        this.index += 1;
      }
      if (this.index === exponentStart) throw new CalculatorError("malformed exponent");
    }

    return this.finite(Number(this.source.slice(start, this.index)));
  }
}

function formatNumber(value) {
  return Object.is(value, -0) ? "-0" : String(value);
}

if (process.argv.length !== 3) {
  console.error("error: expected exactly one expression argument");
  process.exit(1);
}

try {
  const result = new ExpressionParser(process.argv[2]).evaluate();
  console.log(formatNumber(result));
} catch (error) {
  console.error(`error: ${error instanceof Error ? error.message : String(error)}`);
  process.exit(1);
}
