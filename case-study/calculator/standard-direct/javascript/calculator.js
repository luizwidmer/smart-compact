"use strict";

class CalculatorError extends Error {}

class Parser {
  constructor(text) { this.text = text; this.pos = 0; }

  skipSpace() {
    while (this.pos < this.text.length && " \t\n\r\v\f".includes(this.text[this.pos])) this.pos++;
  }

  consume(token) {
    this.skipSpace();
    if (this.text[this.pos] === token) { this.pos++; return true; }
    return false;
  }

  finite(value) {
    if (!Number.isFinite(value)) throw new CalculatorError("non-finite result");
    return value;
  }

  parse() {
    const value = this.additive();
    this.skipSpace();
    if (this.pos !== this.text.length) throw new CalculatorError("unexpected trailing input");
    return value;
  }

  additive() {
    let value = this.multiplicative();
    while (true) {
      if (this.consume("+")) value = this.finite(value + this.multiplicative());
      else if (this.consume("-")) value = this.finite(value - this.multiplicative());
      else return value;
    }
  }

  multiplicative() {
    let value = this.unary();
    while (true) {
      if (this.consume("*")) value = this.finite(value * this.unary());
      else if (this.consume("/")) {
        const divisor = this.unary();
        if (divisor === 0) throw new CalculatorError("division by zero");
        value = this.finite(value / divisor);
      } else if (this.consume("%")) {
        const divisor = this.unary();
        if (divisor === 0) throw new CalculatorError("remainder by zero");
        value = this.finite(value % divisor);
      } else return value;
    }
  }

  unary() {
    if (this.consume("+")) return this.unary();
    if (this.consume("-")) return this.finite(-this.unary());
    return this.power();
  }

  power() {
    let value = this.primary();
    if (this.consume("^")) value = this.finite(Math.pow(value, this.unary()));
    return value;
  }

  primary() {
    if (this.consume("(")) {
      const value = this.additive();
      if (!this.consume(")")) throw new CalculatorError("expected closing parenthesis");
      return value;
    }
    return this.number();
  }

  number() {
    this.skipSpace();
    const start = this.pos;
    let digits = 0;
    while (this.pos < this.text.length && this.text[this.pos] >= "0" && this.text[this.pos] <= "9") {
      this.pos++; digits++;
    }
    if (this.text[this.pos] === ".") {
      this.pos++;
      while (this.pos < this.text.length && this.text[this.pos] >= "0" && this.text[this.pos] <= "9") {
        this.pos++; digits++;
      }
    }
    if (digits === 0) throw new CalculatorError("expected number");
    if (this.text[this.pos] === "e" || this.text[this.pos] === "E") {
      this.pos++;
      if (this.text[this.pos] === "+" || this.text[this.pos] === "-") this.pos++;
      const exponentStart = this.pos;
      while (this.pos < this.text.length && this.text[this.pos] >= "0" && this.text[this.pos] <= "9") this.pos++;
      if (this.pos === exponentStart) throw new CalculatorError("malformed exponent");
    }
    return this.finite(Number(this.text.slice(start, this.pos)));
  }
}

if (process.argv.length !== 3) {
  console.error("error: expected exactly one expression argument");
  process.exit(1);
}

try {
  console.log(Parser.prototype.parse.call(new Parser(process.argv[2])));
} catch (error) {
  console.error(`error: ${error instanceof Error ? error.message : String(error)}`);
  process.exit(1);
}
