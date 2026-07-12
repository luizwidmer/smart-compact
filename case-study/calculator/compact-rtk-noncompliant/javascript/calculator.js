"use strict";

class CalculatorError extends Error {}

class Parser {
  constructor(input) { this.input = input; this.pos = 0; }

  skipSpace() {
    while (this.pos < this.input.length && " \t\n\r\f\v".includes(this.input[this.pos])) this.pos++;
  }

  take(token) {
    this.skipSpace();
    if (this.input[this.pos] === token) { this.pos++; return true; }
    return false;
  }

  checked(value) {
    if (!Number.isFinite(value)) throw new CalculatorError("non-finite result");
    return value;
  }

  parse() {
    const value = this.additive();
    this.skipSpace();
    if (this.pos !== this.input.length) throw new CalculatorError("unexpected trailing input");
    return value;
  }

  additive() {
    let value = this.multiplicative();
    while (true) {
      if (this.take("+")) value = this.checked(value + this.multiplicative());
      else if (this.take("-")) value = this.checked(value - this.multiplicative());
      else return value;
    }
  }

  multiplicative() {
    let value = this.unary();
    while (true) {
      if (this.take("*")) value = this.checked(value * this.unary());
      else if (this.take("/")) {
        const divisor = this.unary();
        if (divisor === 0) throw new CalculatorError("division by zero");
        value = this.checked(value / divisor);
      } else if (this.take("%")) {
        const divisor = this.unary();
        if (divisor === 0) throw new CalculatorError("remainder by zero");
        value = this.checked(value % divisor);
      } else return value;
    }
  }

  unary() {
    if (this.take("+")) return this.unary();
    if (this.take("-")) return this.checked(-this.unary());
    return this.power();
  }

  power() {
    const base = this.primary();
    return this.take("^") ? this.checked(base ** this.unary()) : base;
  }

  primary() {
    if (this.take("(")) {
      const value = this.additive();
      if (!this.take(")")) throw new CalculatorError("expected ')'");
      return value;
    }
    return this.number();
  }

  number() {
    this.skipSpace();
    const start = this.pos;
    let digits = 0;
    while (this.pos < this.input.length && this.input[this.pos] >= "0" && this.input[this.pos] <= "9") { this.pos++; digits++; }
    if (this.input[this.pos] === ".") {
      this.pos++;
      while (this.pos < this.input.length && this.input[this.pos] >= "0" && this.input[this.pos] <= "9") { this.pos++; digits++; }
    }
    if (digits === 0) throw new CalculatorError("expected number");
    if (this.input[this.pos] === "e" || this.input[this.pos] === "E") {
      this.pos++;
      if (this.input[this.pos] === "+" || this.input[this.pos] === "-") this.pos++;
      const exponentStart = this.pos;
      while (this.pos < this.input.length && this.input[this.pos] >= "0" && this.input[this.pos] <= "9") this.pos++;
      if (this.pos === exponentStart) throw new CalculatorError("malformed exponent");
    }
    const value = Number(this.input.slice(start, this.pos));
    if (!Number.isFinite(value)) throw new CalculatorError("non-finite input");
    return value;
  }
}

if (process.argv.length !== 3) {
  console.error("error: expected exactly one expression");
  process.exit(1);
}

try {
  console.log(new Parser(process.argv[2]).parse().toString());
} catch (error) {
  console.error(`error: ${error instanceof Error ? error.message : String(error)}`);
  process.exit(1);
}
