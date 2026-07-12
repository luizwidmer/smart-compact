class CalcError extends Error {}

class Parser {
  constructor(source) {
    this.source = source;
    this.pos = 0;
  }

  static checked(value) {
    if (!Number.isFinite(value)) throw new CalcError("non-finite result");
    return value;
  }

  skipSpace() {
    while (this.pos < this.source.length && " \t\n\r\v\f".includes(this.source[this.pos])) this.pos++;
  }

  take(token) {
    this.skipSpace();
    if (this.source[this.pos] === token) { this.pos++; return true; }
    return false;
  }

  parse() {
    const value = this.parseAdditive();
    this.skipSpace();
    if (this.pos !== this.source.length) throw new CalcError("trailing tokens");
    return value;
  }

  parseAdditive() {
    let value = this.parseMultiplicative();
    while (true) {
      if (this.take("+")) value = Parser.checked(value + this.parseMultiplicative());
      else if (this.take("-")) value = Parser.checked(value - this.parseMultiplicative());
      else return value;
    }
  }

  parseMultiplicative() {
    let value = this.parseUnary();
    while (true) {
      if (this.take("*")) value = Parser.checked(value * this.parseUnary());
      else if (this.take("/")) {
        const rhs = this.parseUnary();
        if (rhs === 0) throw new CalcError("division by zero");
        value = Parser.checked(value / rhs);
      } else if (this.take("%")) {
        const rhs = this.parseUnary();
        if (rhs === 0) throw new CalcError("remainder by zero");
        value = Parser.checked(value % rhs);
      } else return value;
    }
  }

  parseUnary() {
    if (this.take("+")) return this.parseUnary();
    if (this.take("-")) return Parser.checked(-this.parseUnary());
    return this.parsePower();
  }

  parsePower() {
    const value = this.parsePrimary();
    if (this.take("^")) return Parser.checked(value ** this.parseUnary());
    return value;
  }

  parsePrimary() {
    this.skipSpace();
    if (this.take("(")) {
      const value = this.parseAdditive();
      if (!this.take(")")) throw new CalcError("missing closing parenthesis");
      return value;
    }

    const start = this.pos;
    let before = 0;
    while (this.pos < this.source.length && this.source.charCodeAt(this.pos) >= 48 && this.source.charCodeAt(this.pos) <= 57) { this.pos++; before++; }
    let after = 0;
    if (this.source[this.pos] === ".") {
      this.pos++;
      while (this.pos < this.source.length && this.source.charCodeAt(this.pos) >= 48 && this.source.charCodeAt(this.pos) <= 57) { this.pos++; after++; }
    }
    if (before === 0 && after === 0) throw new CalcError("expected number or parenthesis");
    if (this.source[this.pos] === "e" || this.source[this.pos] === "E") {
      this.pos++;
      if (this.source[this.pos] === "+" || this.source[this.pos] === "-") this.pos++;
      const exponentStart = this.pos;
      while (this.pos < this.source.length && this.source.charCodeAt(this.pos) >= 48 && this.source.charCodeAt(this.pos) <= 57) this.pos++;
      if (this.pos === exponentStart) throw new CalcError("invalid exponent");
    }
    const value = Number(this.source.slice(start, this.pos));
    return Parser.checked(value);
  }
}

if (process.argv.length !== 3) {
  console.error("error: expected exactly one expression");
  process.exit(1);
}
try {
  const result = new Parser(process.argv[2]).parse();
  console.log(result.toPrecision(17));
} catch (error) {
  console.error(`error: ${error instanceof CalcError ? error.message : "calculator failure"}`);
  process.exit(1);
}
