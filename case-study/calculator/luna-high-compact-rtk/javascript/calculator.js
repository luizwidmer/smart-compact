"use strict";

class CalcError extends Error {}

class Parser {
  constructor(text) {
    this.text = text;
    this.pos = 0;
  }

  whitespace() {
    while (this.pos < this.text.length && " \t\n\r\v\f".includes(this.text[this.pos])) this.pos++;
  }

  number() {
    this.whitespace();
    const start = this.pos;
    let digits = 0;
    while (this.pos < this.text.length && this.text[this.pos] >= "0" && this.text[this.pos] <= "9") { this.pos++; digits++; }
    if (this.pos < this.text.length && this.text[this.pos] === ".") {
      this.pos++;
      while (this.pos < this.text.length && this.text[this.pos] >= "0" && this.text[this.pos] <= "9") { this.pos++; digits++; }
    }
    if (digits === 0) { this.pos = start; throw new CalcError("expected number"); }
    if (this.pos < this.text.length && "eE".includes(this.text[this.pos])) {
      this.pos++;
      if (this.pos < this.text.length && "+-".includes(this.text[this.pos])) this.pos++;
      const exponentStart = this.pos;
      while (this.pos < this.text.length && this.text[this.pos] >= "0" && this.text[this.pos] <= "9") this.pos++;
      if (this.pos === exponentStart) throw new CalcError("malformed exponent");
    }
    const value = Number(this.text.slice(start, this.pos));
    if (!Number.isFinite(value)) throw new CalcError("non-finite number");
    return value;
  }

  primary() {
    this.whitespace();
    if (this.pos < this.text.length && this.text[this.pos] === "(") {
      this.pos++;
      const value = this.additive();
      this.whitespace();
      if (this.pos >= this.text.length || this.text[this.pos] !== ")") throw new CalcError("expected closing parenthesis");
      this.pos++;
      return value;
    }
    return this.number();
  }

  power() {
    let value = this.primary();
    this.whitespace();
    if (this.pos < this.text.length && this.text[this.pos] === "^") {
      this.pos++;
      value = Math.pow(value, this.unary());
      if (!Number.isFinite(value)) throw new CalcError("non-finite result");
    }
    return value;
  }

  unary() {
    this.whitespace();
    if (this.pos < this.text.length && "+-".includes(this.text[this.pos])) {
      const negative = this.text[this.pos] === "-";
      this.pos++;
      const value = this.unary();
      return negative ? -value : value;
    }
    return this.power();
  }

  multiplicative() {
    let value = this.unary();
    while (true) {
      this.whitespace();
      if (this.pos >= this.text.length || !"*/%".includes(this.text[this.pos])) return value;
      const op = this.text[this.pos++];
      const right = this.unary();
      if (right === 0) throw new CalcError("division by zero");
      if (op === "*") value *= right;
      else if (op === "/") value /= right;
      else value %= right;
      if (!Number.isFinite(value)) throw new CalcError("non-finite result");
    }
  }

  additive() {
    let value = this.multiplicative();
    while (true) {
      this.whitespace();
      if (this.pos >= this.text.length || !"+-".includes(this.text[this.pos])) return value;
      const op = this.text[this.pos++];
      const right = this.multiplicative();
      value = op === "+" ? value + right : value - right;
      if (!Number.isFinite(value)) throw new CalcError("non-finite result");
    }
  }

  parse() {
    this.whitespace();
    if (this.pos === this.text.length) throw new CalcError("empty expression");
    const value = this.additive();
    this.whitespace();
    if (this.pos !== this.text.length) throw new CalcError("trailing tokens");
    return value;
  }
}

try {
  if (process.argv.length !== 3) throw new CalcError("expected exactly one expression");
  console.log(new Parser(process.argv[2]).parse());
} catch (error) {
  console.error(`error: ${error instanceof CalcError ? error.message : "calculator failure"}`);
  process.exitCode = 1;
}
