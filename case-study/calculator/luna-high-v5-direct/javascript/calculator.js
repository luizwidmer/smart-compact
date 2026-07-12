"use strict";

const NUMBER = /(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?/y;

class ParseError extends Error {}

class Parser {
  constructor(source) {
    this.source = source;
    this.position = 0;
  }

  skipSpace() {
    while (this.position < this.source.length && this.source.charCodeAt(this.position) < 128 && /\s/.test(this.source[this.position])) this.position++;
  }

  take(character) {
    this.skipSpace();
    if (this.source[this.position] === character) { this.position++; return true; }
    return false;
  }

  parse() {
    const result = this.parseAdditive();
    this.skipSpace();
    if (this.position !== this.source.length) throw new ParseError("trailing tokens");
    return result;
  }

  parseAdditive() {
    let result = this.parseMultiplicative();
    while (true) {
      if (this.take("+")) result = this.checked(result + this.parseMultiplicative());
      else if (this.take("-")) result = this.checked(result - this.parseMultiplicative());
      else return result;
    }
  }

  parseMultiplicative() {
    let result = this.parseUnary();
    while (true) {
      if (this.take("*")) result = this.checked(result * this.parseUnary());
      else if (this.take("/")) {
        const right = this.parseUnary();
        if (right === 0) throw new ParseError("division by zero");
        result = this.checked(result / right);
      } else if (this.take("%")) {
        const right = this.parseUnary();
        if (right === 0) throw new ParseError("remainder by zero");
        result = this.checked(result % right);
      } else return result;
    }
  }

  parseUnary() {
    if (this.take("+")) return this.parseUnary();
    if (this.take("-")) return this.checked(-this.parseUnary());
    return this.parsePower();
  }

  parsePower() {
    const result = this.parsePrimary();
    if (this.take("^")) return this.checked(result ** this.parseUnary());
    return result;
  }

  parsePrimary() {
    if (this.take("(")) {
      const result = this.parseAdditive();
      if (!this.take(")")) throw new ParseError("expected ')'");
      return result;
    }
    this.skipSpace();
    NUMBER.lastIndex = this.position;
    const match = NUMBER.exec(this.source);
    if (!match) throw new ParseError("expected number or '('");
    this.position = NUMBER.lastIndex;
    return this.checked(Number(match[0]));
  }

  checked(value) {
    if (!Number.isFinite(value)) throw new ParseError("non-finite result");
    return value;
  }
}

if (process.argv.length !== 3) {
  console.error("error: expected exactly one expression");
  process.exit(1);
}
try {
  console.log(String(new Parser(process.argv[2]).parse()));
} catch (error) {
  console.error(`error: ${error instanceof Error ? error.message : "calculator failure"}`);
  process.exit(1);
}
