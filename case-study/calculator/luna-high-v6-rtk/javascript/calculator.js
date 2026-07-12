"use strict";

class ParseError extends Error {}
const isDigit = (c) => c >= "0" && c <= "9";

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
  checked(value) {
    if (!Number.isFinite(value)) throw new ParseError("non-finite result");
    return value;
  }
  parse() {
    const value = this.addition();
    this.skipSpace();
    if (this.pos !== this.text.length) throw new ParseError("trailing token");
    return value;
  }
  addition() {
    let value = this.multiplication();
    while (true) {
      if (this.take("+")) value = this.checked(value + this.multiplication());
      else if (this.take("-")) value = this.checked(value - this.multiplication());
      else return value;
    }
  }
  multiplication() {
    let value = this.unary();
    while (true) {
      if (this.take("*")) value = this.checked(value * this.unary());
      else if (this.take("/")) {
        const right = this.unary();
        if (right === 0) throw new ParseError("division by zero");
        value = this.checked(value / right);
      } else if (this.take("%")) {
        const right = this.unary();
        if (right === 0) throw new ParseError("remainder by zero");
        value = this.checked(value % right);
      } else return value;
    }
  }
  unary() {
    if (this.take("+")) return this.unary();
    if (this.take("-")) return this.checked(-this.unary());
    return this.power();
  }
  power() {
    const value = this.primary();
    if (this.take("^")) return this.checked(value ** this.unary());
    return value;
  }
  primary() {
    if (this.take("(")) {
      const value = this.addition();
      if (!this.take(")")) throw new ParseError("missing closing parenthesis");
      return value;
    }
    this.skipSpace();
    const start = this.pos;
    let digits = 0;
    while (isDigit(this.text[this.pos])) { this.pos++; digits++; }
    if (this.text[this.pos] === ".") {
      this.pos++;
      while (isDigit(this.text[this.pos])) this.pos++;
    } else if (digits === 0) throw new ParseError("expected number or parenthesis");
    if (this.text[this.pos] === "e" || this.text[this.pos] === "E") {
      this.pos++;
      if (this.text[this.pos] === "+" || this.text[this.pos] === "-") this.pos++;
      const exponentStart = this.pos;
      while (isDigit(this.text[this.pos])) this.pos++;
      if (exponentStart === this.pos) throw new ParseError("invalid exponent");
    }
    const value = Number(this.text.slice(start, this.pos));
    return this.checked(value);
  }
}

if (process.argv.length !== 3) {
  console.error("error: expected exactly one expression");
  process.exit(2);
}
try {
  console.log(String(new Parser(process.argv[2]).parse()));
} catch (error) {
  console.error(`error: ${error instanceof Error ? error.message : "invalid expression"}`);
  process.exit(1);
}
