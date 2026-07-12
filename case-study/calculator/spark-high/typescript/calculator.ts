#!/usr/bin/env node

const args = process.argv;
const expr = args[2];

if (args.length !== 3) {
  console.error("error: expected one expression argument");
  process.exit(1);
}

class Parser {
  private readonly text: string;
  private pos: number = 0;
  private readonly len: number;

  constructor(text: string) {
    this.text = text;
    this.len = text.length;
  }

  parse(): number {
    this.skipWs();
    if (this.pos >= this.len) {
      throw new Error("empty expression");
    }
    const value = this.parseAddSub();
    this.skipWs();
    if (this.pos !== this.len) {
      throw new Error("unexpected token");
    }
    if (!Number.isFinite(value)) {
      throw new Error("non-finite result");
    }
    return value;
  }

  private parseAddSub(): number {
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

  private parseMulDiv(): number {
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

  private parseUnary(): number {
    this.skipWs();
    if (this.consume("+")) {
      return this.parseUnary();
    }
    if (this.consume("-")) {
      return -this.parseUnary();
    }
    return this.parsePow();
  }

  private parsePow(): number {
    const value = this.parsePrimary();
    this.skipWs();
    if (this.consume("^")) {
      const rhs = this.parsePow();
      return Math.pow(value, rhs);
    }
    return value;
  }

  private parsePrimary(): number {
    this.skipWs();
    if (this.consume("(")) {
      const value = this.parseAddSub();
      this.skipWs();
      if (!this.consume(")")) {
        throw new Error("missing closing parenthesis");
      }
      return value;
    }
    return this.parseNumber();
  }

  private parseNumber(): number {
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

    const ch = this.peek();
    if (ch === "e" || ch === "E") {
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
    if (!Number.isFinite(value)) {
      throw new Error("non-finite number");
    }
    if (Number.isNaN(value)) {
      throw new Error("malformed number");
    }
    return value;
  }

  private isDigit(ch: string): boolean {
    return ch >= "0" && ch <= "9";
  }

  private peek(): string {
    return this.text[this.pos] ?? "";
  }

  private consume(ch: string): boolean {
    if (this.text[this.pos] === ch) {
      this.pos++;
      return true;
    }
    return false;
  }

  private skipWs(): void {
    while (this.pos < this.len && /\s/.test(this.text[this.pos])) {
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
