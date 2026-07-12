#!/usr/bin/env node
class Parser {
  constructor(expression) {
    this.expression = expression;
    this.pos = 0;
  }

  parse() {
    const value = this.parseExpr();
    this.skipWs();
    if (this.pos !== this.expression.length) {
      throw new Error("trailing input");
    }
    return value;
  }

  skipWs() {
    while (this.pos < this.expression.length && /\s/.test(this.expression[this.pos])) {
      this.pos += 1;
    }
  }

  parseExpr() {
    let left = this.parseTerm();
    while (true) {
      this.skipWs();
      const ch = this.expression[this.pos];
      if (ch === "+") {
        this.pos += 1;
        left = this.ensureFinite(left + this.parseTerm());
      } else if (ch === "-") {
        this.pos += 1;
        left = this.ensureFinite(left - this.parseTerm());
      } else {
        return left;
      }
    }
  }

  parseTerm() {
    let left = this.parsePow();
    while (true) {
      this.skipWs();
      const ch = this.expression[this.pos];
      if (ch === "*") {
        this.pos += 1;
        left = this.ensureFinite(left * this.parsePow());
      } else if (ch === "/") {
        this.pos += 1;
        const rhs = this.parsePow();
        if (rhs === 0) {
          throw new Error("division by zero");
        }
        left = this.ensureFinite(left / rhs);
      } else if (ch === "%") {
        this.pos += 1;
        const rhs = this.parsePow();
        if (rhs === 0) {
          throw new Error("remainder by zero");
        }
        left = this.ensureFinite(left % rhs);
      } else {
        return left;
      }
    }
  }

  parsePow() {
    const left = this.parseUnary();
    this.skipWs();
    if (this.expression[this.pos] === "^") {
      this.pos += 1;
      return this.ensureFinite(Math.pow(left, this.parsePow()));
    }
    return left;
  }

  parseUnary() {
    this.skipWs();
    if (this.expression[this.pos] === "+") {
      this.pos += 1;
      return this.parseUnary();
    }
    if (this.expression[this.pos] === "-") {
      this.pos += 1;
      return this.ensureFinite(-this.parseUnary());
    }
    return this.parsePrimary();
  }

  parsePrimary() {
    this.skipWs();
    const ch = this.expression[this.pos];
    if (ch === "(") {
      this.pos += 1;
      const value = this.parseExpr();
      this.skipWs();
      if (this.expression[this.pos] !== ")") {
        throw new Error("missing ')'");
      }
      this.pos += 1;
      return value;
    }
    if (ch === undefined) {
      throw new Error("unexpected end of input");
    }
    if (ch === "." || (ch >= "0" && ch <= "9")) {
      return this.parseNumber();
    }
    throw new Error(`unexpected token '${ch}'`);
  }

  parseNumber() {
    this.skipWs();
    const input = this.expression.slice(this.pos);
    const match = input.match(/^(?:\d+\.\d*|\d+|\.\d+)(?:[eE][+-]?\d+)?/);
    if (!match) {
      throw new Error("invalid number");
    }
    const token = match[0];
    this.pos += token.length;
    const value = Number(token);
    return this.ensureFinite(value);
  }

  ensureFinite(value) {
    if (!Number.isFinite(value)) {
      throw new Error("non-finite value");
    }
    return value;
  }
}

if (process.argv.length !== 3) {
  console.error("error: expected exactly one expression argument");
  process.exit(1);
}

try {
  const parser = new Parser(process.argv[2]);
  const value = parser.parse();
  console.log(String(value));
  process.exit(0);
} catch (error) {
  console.error(`error: ${error.message}`);
  process.exit(1);
}
