"use strict";

class CalculatorError extends Error {}

class Parser {
  constructor(text) { this.text = text; this.pos = 0; }

  skipWhitespace() {
    while (this.pos < this.text.length && " \t\n\r\f\v".includes(this.text[this.pos])) this.pos++;
  }

  consume(token) {
    this.skipWhitespace();
    if (this.text[this.pos] === token) { this.pos++; return true; }
    return false;
  }

  checked(value) {
    if (!Number.isFinite(value)) throw new CalculatorError("non-finite result");
    return value;
  }

  parse() {
    const value = this.expression();
    this.skipWhitespace();
    if (this.pos !== this.text.length) throw new CalculatorError("unexpected trailing input");
    return value;
  }

  expression() {
    let value = this.term();
    for (;;) {
      if (this.consume("+")) value = this.checked(value + this.term());
      else if (this.consume("-")) value = this.checked(value - this.term());
      else return value;
    }
  }

  term() {
    let value = this.unary();
    for (;;) {
      if (this.consume("*")) value = this.checked(value * this.unary());
      else if (this.consume("/")) {
        const divisor = this.unary();
        if (divisor === 0) throw new CalculatorError("division by zero");
        value = this.checked(value / divisor);
      } else if (this.consume("%")) {
        const divisor = this.unary();
        if (divisor === 0) throw new CalculatorError("remainder by zero");
        value = this.checked(value % divisor);
      } else return value;
    }
  }

  unary() {
    if (this.consume("+")) return this.checked(+this.unary());
    if (this.consume("-")) return this.checked(-this.unary());
    return this.power();
  }

  power() {
    const base = this.primary();
    if (this.consume("^")) return this.checked(Math.pow(base, this.unary()));
    return base;
  }

  primary() {
    if (this.consume("(")) {
      const value = this.expression();
      if (!this.consume(")")) throw new CalculatorError("expected ')'");
      return value;
    }
    return this.number();
  }

  number() {
    this.skipWhitespace();
    const start = this.pos;
    let digits = 0;
    while (this.pos < this.text.length && this.text.charCodeAt(this.pos) >= 48 && this.text.charCodeAt(this.pos) <= 57) { this.pos++; digits++; }
    if (this.text[this.pos] === ".") {
      this.pos++;
      while (this.pos < this.text.length && this.text.charCodeAt(this.pos) >= 48 && this.text.charCodeAt(this.pos) <= 57) { this.pos++; digits++; }
    }
    if (digits === 0) throw new CalculatorError("expected number");
    if (this.text[this.pos] === "e" || this.text[this.pos] === "E") {
      this.pos++;
      if (this.text[this.pos] === "+" || this.text[this.pos] === "-") this.pos++;
      const exponentStart = this.pos;
      while (this.pos < this.text.length && this.text.charCodeAt(this.pos) >= 48 && this.text.charCodeAt(this.pos) <= 57) this.pos++;
      if (this.pos === exponentStart) throw new CalculatorError("malformed exponent");
    }
    return this.checked(Number(this.text.slice(start, this.pos)));
  }
}

if (process.argv.length !== 3) {
  console.error("error: expected exactly one expression argument");
  process.exit(1);
}

try {
  console.log(new Parser(process.argv[2]).parse().toString());
} catch (error) {
  console.error(`error: ${error instanceof Error ? error.message : String(error)}`);
  process.exit(1);
}
