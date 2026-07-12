#!/usr/bin/env node

const tokenFromArg = process.argv;
const expr = tokenFromArg[2];

if (tokenFromArg.length !== 3) {
  console.error("error: expected one expression argument");
  process.exit(1);
}

function isWs(ch) {
  return /\s/.test(ch);
}

class Parser {
  constructor(text) {
    this.text = text;
    this.pos = 0;
    this.len = text.length;
  }

  parse() {
    this.skipWs();
    if (this.pos >= this.len) throw new Error("empty expression");
    const value = this.parseAddSub();
    this.skipWs();
    if (this.pos !== this.len) throw new Error("unexpected token");
    if (!Number.isFinite(value)) throw new Error("non-finite result");
    return value;
  }

  parseAddSub() {
    let value = this.parseMulDiv();
    while (true) {
      this.skipWs();
      if (this.consume("+")) {
        value += this.parseMulDiv();
      } else if (this.consume("-")) {
        value -= this.parseMulDiv();
      } else {
        break;
      }
    }
    return value;
  }

  parseMulDiv() {
    let value = this.parseUnary();
    while (true) {
      this.skipWs();
      if (this.consume("*")) {
        value *= this.parseUnary();
      } else if (this.consume("/")) {
        const rhs = this.parseUnary();
        if (rhs === 0) throw new Error("division by zero");
        value /= rhs;
      } else if (this.consume("%")) {
        const rhs = this.parseUnary();
        if (rhs === 0) throw new Error("remainder by zero");
        value %= rhs;
      } else {
        break;
      }
    }
    return value;
  }

  parseUnary() {
    this.skipWs();
    if (this.consume("+")) {
      return this.parseUnary();
    }
    if (this.consume("-")) {
      return -this.parseUnary();
    }
    return this.parsePow();
  }

  parsePow() {
    let value = this.parsePrimary();
    this.skipWs();
    if (this.consume("^")) {
      const rhs = this.parsePow();
      value = Math.pow(value, rhs);
    }
    return value;
  }

  parsePrimary() {
    this.skipWs();
    if (this.consume("(")) {
      const value = this.parseAddSub();
      this.skipWs();
      if (!this.consume(")")) throw new Error("missing closing parenthesis");
      return value;
    }
    return this.parseNumber();
  }

  parseNumber() {
    const start = this.pos;
    let sawDigitsBefore = false;

    if (this.peek() === ".") {
      this.pos++;
      if (this.pos >= this.len || !this.isDigit(this.peek())) {
        throw new Error("malformed number");
      }
      while (this.pos < this.len && this.isDigit(this.peek())) {
        this.pos++;
      }
    } else {
      while (this.pos < this.len && this.isDigit(this.peek())) {
        this.pos++;
        sawDigitsBefore = true;
      }
      if (this.peek() === ".") {
        this.pos++;
        while (this.pos < this.len && this.isDigit(this.peek())) {
          this.pos++;
        }
      } else if (!sawDigitsBefore) {
        throw new Error("malformed number");
      }
    }

    if (this.peek() === "e" || this.peek() === "E") {
      this.pos++;
      if (this.peek() === "+" || this.peek() === "-") {
        this.pos++;
      }
      if (this.pos >= this.len || !this.isDigit(this.peek())) {
        throw new Error("malformed number");
      }
      while (this.pos < this.len && this.isDigit(this.peek())) {
        this.pos++;
      }
    }

    const token = this.text.slice(start, this.pos);
    const value = Number.parseFloat(token);
    if (!Number.isFinite(value)) throw new Error("non-finite number");
    if (Number.isNaN(value)) throw new Error("malformed number");
    return value;
  }

  isDigit(ch) {
    return ch >= "0" && ch <= "9";
  }

  peek() {
    return this.text[this.pos] ?? "";
  }

  consume(ch) {
    if (this.text[this.pos] === ch) {
      this.pos += 1;
      return true;
    }
    return false;
  }

  skipWs() {
    while (this.pos < this.len && isWs(this.text[this.pos])) {
      this.pos++;
    }
  }
}

try {
  const parser = new Parser(expr);
  const result = parser.parse();
  const output = Number.isInteger(result) ? String(Math.trunc(result)) : String(result);
  console.log(output);
  process.exit(0);
} catch (error) {
  const message = error instanceof Error ? error.message : String(error);
  console.error(`error: ${message}`);
  process.exit(1);
}
