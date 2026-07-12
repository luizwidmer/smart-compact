class CalculatorError extends Error {}

class Parser {
  constructor(source) {
    this.source = source;
    this.position = 0;
  }

  fail(message) {
    throw new CalculatorError(message);
  }

  skipSpace() {
    while (this.position < this.source.length && " \t\n\r\v\f".includes(this.source[this.position])) this.position += 1;
  }

  parseNumber() {
    this.skipSpace();
    const start = this.position;
    let before = 0;
    while (this.position < this.source.length && this.source.charCodeAt(this.position) >= 48 && this.source.charCodeAt(this.position) <= 57) {
      this.position += 1;
      before += 1;
    }
    let after = 0;
    if (this.source[this.position] === ".") {
      this.position += 1;
      while (this.position < this.source.length && this.source.charCodeAt(this.position) >= 48 && this.source.charCodeAt(this.position) <= 57) {
        this.position += 1;
        after += 1;
      }
    }
    if (before + after === 0) this.fail("expected number");
    if (this.source[this.position] === "e" || this.source[this.position] === "E") {
      this.position += 1;
      if (this.source[this.position] === "+" || this.source[this.position] === "-") this.position += 1;
      const exponentStart = this.position;
      while (this.position < this.source.length && this.source.charCodeAt(this.position) >= 48 && this.source.charCodeAt(this.position) <= 57) this.position += 1;
      if (this.position === exponentStart) this.fail("invalid exponent");
    }
    const value = Number(this.source.slice(start, this.position));
    if (!Number.isFinite(value)) this.fail("non-finite number");
    return value;
  }

  parsePrimary() {
    this.skipSpace();
    if (this.source[this.position] === "(") {
      this.position += 1;
      const value = this.parseAdditive();
      this.skipSpace();
      if (this.source[this.position] !== ")") this.fail("expected ')'");
      this.position += 1;
      return value;
    }
    return this.parseNumber();
  }

  parsePower() {
    let value = this.parsePrimary();
    this.skipSpace();
    if (this.source[this.position] === "^") {
      this.position += 1;
      value = Math.pow(value, this.parseUnary());
      if (!Number.isFinite(value)) this.fail("non-finite result");
    }
    return value;
  }

  parseUnary() {
    this.skipSpace();
    if (this.source[this.position] === "+" || this.source[this.position] === "-") {
      const negative = this.source[this.position] === "-";
      this.position += 1;
      const value = this.parseUnary();
      return negative ? -value : value;
    }
    return this.parsePower();
  }

  parseMultiplicative() {
    let value = this.parseUnary();
    while (true) {
      this.skipSpace();
      const operation = this.source[this.position];
      if (operation !== "*" && operation !== "/" && operation !== "%") return value;
      this.position += 1;
      const right = this.parseUnary();
      if (right === 0) this.fail("division by zero");
      value = operation === "*" ? value * right : operation === "/" ? value / right : value % right;
      if (!Number.isFinite(value)) this.fail("non-finite result");
    }
  }

  parseAdditive() {
    let value = this.parseMultiplicative();
    while (true) {
      this.skipSpace();
      const operation = this.source[this.position];
      if (operation !== "+" && operation !== "-") return value;
      this.position += 1;
      const right = this.parseMultiplicative();
      value = operation === "+" ? value + right : value - right;
      if (!Number.isFinite(value)) this.fail("non-finite result");
    }
  }

  parse() {
    const value = this.parseAdditive();
    this.skipSpace();
    if (this.position !== this.source.length) this.fail("unexpected token");
    return value;
  }
}

const args = process.argv.slice(2);
if (args.length !== 1) {
  console.error("error: expected exactly one expression");
  process.exit(1);
}
try {
  console.log(String(new Parser(args[0]).parse()));
} catch (error) {
  console.error(`error: ${error instanceof CalculatorError ? error.message : "invalid expression"}`);
  process.exit(1);
}
