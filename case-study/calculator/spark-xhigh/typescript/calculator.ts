#!/usr/bin/env node

class ParseError extends Error {
  constructor(message: string) {
    super(`error: ${message}`);
    this.name = "ParseError";
  }
}

class Parser {
  private expr: string;
  private pos = 0;

  constructor(expression: string) {
    this.expr = expression;
  }

  parse(): number {
    const value = this.parseExpr();
    this.skipWs();
    if (this.pos !== this.expr.length) {
      throw new ParseError("trailing input");
    }
    return value;
  }

  private parseExpr(): number {
    let left = this.parseTerm();
    while (true) {
      this.skipWs();
      const ch = this.expr[this.pos];
      if (ch === "+") {
        this.pos++;
        left = this.ensureFinite(left + this.parseTerm());
      } else if (ch === "-") {
        this.pos++;
        left = this.ensureFinite(left - this.parseTerm());
      } else {
        return left;
      }
    }
  }

  private parseTerm(): number {
    let left = this.parsePow();
    while (true) {
      this.skipWs();
      const ch = this.expr[this.pos];
      if (ch === "*") {
        this.pos++;
        left = this.ensureFinite(left * this.parsePow());
      } else if (ch === "/") {
        this.pos++;
        const rhs = this.parsePow();
        if (rhs === 0.0) {
          throw new ParseError("division by zero");
        }
        left = this.ensureFinite(left / rhs);
      } else if (ch === "%") {
        this.pos++;
        const rhs = this.parsePow();
        if (rhs === 0.0) {
          throw new ParseError("remainder by zero");
        }
        left = this.ensureFinite(left % rhs);
      } else {
        return left;
      }
    }
  }

  private parsePow(): number {
    const left = this.parseUnary();
    this.skipWs();
    if (this.expr[this.pos] === "^") {
      this.pos++;
      return this.ensureFinite(left ** this.parsePow());
    }
    return left;
  }

  private parseUnary(): number {
    this.skipWs();
    if (this.expr[this.pos] === "+") {
      this.pos++;
      return this.parseUnary();
    }
    if (this.expr[this.pos] === "-") {
      this.pos++;
      return this.ensureFinite(-this.parseUnary());
    }
    return this.parsePrimary();
  }

  private parsePrimary(): number {
    this.skipWs();
    const ch = this.expr[this.pos];
    if (ch === "(") {
      this.pos++;
      const value = this.parseExpr();
      this.skipWs();
      if (this.expr[this.pos] !== ")") {
        throw new ParseError("missing ')'");
      }
      this.pos++;
      return value;
    }
    if (ch === undefined) {
      throw new ParseError("unexpected end of input");
    }
    if (ch === "." || (ch >= "0" && ch <= "9")) {
      return this.parseNumber();
    }
    throw new ParseError(`unexpected token '${ch}'`);
  }

  private parseNumber(): number {
    this.skipWs();
    const input = this.expr.slice(this.pos);
    const match = input.match(/^(?:\d+\.\d*|\d+|\.\d+)(?:[eE][+-]?\d+)?/);
    if (!match) {
      throw new ParseError("invalid number");
    }
    const token = match[0];
    this.pos += token.length;
    const value = Number(token);
    return this.ensureFinite(value);
  }

  private parseExprEnd(): void {
    this.skipWs();
  }

  private skipWs(): void {
    while (this.pos < this.expr.length && /\s/.test(this.expr[this.pos])) {
      this.pos++;
    }
  }

  private ensureFinite(value: number): number {
    if (!Number.isFinite(value)) {
      throw new ParseError("non-finite value");
    }
    return value;
  }
}

const args = process.argv;
if (args.length !== 3) {
  console.error("error: expected exactly one expression argument");
  process.exit(1);
}

try {
  const parser = new Parser(args[2]);
  const value = parser.parse();
  console.log(String(value));
  process.exit(0);
} catch (error) {
  if (error instanceof ParseError) {
    console.error(error.message);
  } else if (error instanceof Error) {
    console.error(`error: ${error.message}`);
  } else {
    console.error("error: parser failure");
  }
  process.exit(1);
}
