"use strict";

class ParseError extends Error {}
const isDigit = (c: string | undefined): boolean => c !== undefined && c >= "0" && c <= "9";

class Parser {
  private pos = 0;
  private readonly text: string;
  constructor(text: string) { this.text = text; }
  private skipSpace(): void {
    while (this.pos < this.text.length && " \t\n\r\v\f".includes(this.text[this.pos])) this.pos++;
  }
  private take(char: string): boolean {
    this.skipSpace();
    if (this.text[this.pos] === char) { this.pos++; return true; }
    return false;
  }
  private checked(value: number): number {
    if (!Number.isFinite(value)) throw new ParseError("non-finite result");
    return value;
  }
  parse(): number {
    const value = this.addition();
    this.skipSpace();
    if (this.pos !== this.text.length) throw new ParseError("trailing token");
    return value;
  }
  private addition(): number {
    let value = this.multiplication();
    while (true) {
      if (this.take("+")) value = this.checked(value + this.multiplication());
      else if (this.take("-")) value = this.checked(value - this.multiplication());
      else return value;
    }
  }
  private multiplication(): number {
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
  private unary(): number {
    if (this.take("+")) return this.unary();
    if (this.take("-")) return this.checked(-this.unary());
    return this.power();
  }
  private power(): number {
    const value = this.primary();
    if (this.take("^")) return this.checked(value ** this.unary());
    return value;
  }
  private primary(): number {
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
    return this.checked(Number(this.text.slice(start, this.pos)));
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
