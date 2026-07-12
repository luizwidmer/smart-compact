"use strict";

class CalculatorError extends Error {}

class Parser {
  constructor(text) { this.text = text; this.pos = 0; }

  skipSpace() {
    while (this.pos < this.text.length && " \t\n\r\v\f".includes(this.text[this.pos])) this.pos++;
  }

  take(char) {
    this.skipSpace();
    if (this.text[this.pos] === char) { this.pos++; return true; }
    return false;
  }

  parse() {
    const value = this.additive();
    this.skipSpace();
    if (this.pos !== this.text.length) throw new CalculatorError("unexpected token");
    return value;
  }

  additive() {
    let value = this.multiplicative();
    while (true) {
      if (this.take("+")) value = checked(value + this.multiplicative());
      else if (this.take("-")) value = checked(value - this.multiplicative());
      else return value;
    }
  }

  multiplicative() {
    let value = this.unary();
    while (true) {
      if (this.take("*")) value = checked(value * this.unary());
      else if (this.take("/")) {
        const divisor = this.unary();
        if (divisor === 0) throw new CalculatorError("division by zero");
        value = checked(value / divisor);
      } else if (this.take("%")) {
        const divisor = this.unary();
        if (divisor === 0) throw new CalculatorError("remainder by zero");
        value = checked(value % divisor);
      } else return value;
    }
  }

  unary() {
    if (this.take("+")) return this.unary();
    if (this.take("-")) return checked(-this.unary());
    return this.power();
  }

  power() {
    let value = this.primary();
    if (this.take("^")) value = checked(Math.pow(value, this.unary()));
    return value;
  }

  primary() {
    if (this.take("(")) {
      const value = this.additive();
      if (!this.take(")")) throw new CalculatorError("expected closing parenthesis");
      return value;
    }
    return this.number();
  }

  number() {
    this.skipSpace();
    const start = this.pos;
    let before = 0;
    while (isDigit(this.text[this.pos])) { this.pos++; before++; }
    let after = 0;
    if (this.text[this.pos] === ".") {
      this.pos++;
      while (isDigit(this.text[this.pos])) { this.pos++; after++; }
    }
    if (before === 0 && after === 0) throw new CalculatorError("expected number");
    if (this.text[this.pos] === "e" || this.text[this.pos] === "E") {
      this.pos++;
      if (this.text[this.pos] === "+" || this.text[this.pos] === "-") this.pos++;
      const exponentStart = this.pos;
      while (isDigit(this.text[this.pos])) this.pos++;
      if (this.pos === exponentStart) throw new CalculatorError("malformed exponent");
    }
    return checked(Number(this.text.slice(start, this.pos)));
  }
}

function isDigit(char) { return char !== undefined && char >= "0" && char <= "9"; }
function checked(value) {
  if (!Number.isFinite(value)) throw new CalculatorError("non-finite result");
  return value;
}

if (process.argv.length !== 3) {
  console.error("error: expected exactly one expression");
  process.exit(1);
}
try {
  console.log(Parser.prototype.parse.call(new Parser(process.argv[2])));
} catch (error) {
  console.error(`error: ${error instanceof Error ? error.message : String(error)}`);
  process.exit(1);
}
