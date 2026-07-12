#!/usr/bin/env node
'use strict';

const args = process.argv;
if (args.length !== 3) {
  console.error('error: expected exactly one expression argument');
  process.exit(1);
}

class Parser {
  private s: string;
  private i = 0;
  private n: number;

  constructor(text: string) {
    this.s = text;
    this.n = text.length;
  }

  parse(): number {
    const value = this.parseExpr();
    this.skipWs();
    if (this.i !== this.n) {
      throw new Error('trailing tokens');
    }
    if (!Number.isFinite(value)) {
      throw new Error('non-finite result');
    }
    return value;
  }

  private parseExpr(): number {
    return this.parseAdd();
  }

  private parseAdd(): number {
    let value = this.parseMul();
    while (true) {
      this.skipWs();
      if (this.match('+')) {
        value += this.parseMul();
      } else if (this.match('-')) {
        value -= this.parseMul();
      } else {
        break;
      }
      if (!Number.isFinite(value)) throw new Error('non-finite result');
    }
    return value;
  }

  private parseMul(): number {
    let value = this.parseUnary();
    while (true) {
      this.skipWs();
      if (this.match('*')) {
        value *= this.parseUnary();
      } else if (this.match('/')) {
        const rhs = this.parseUnary();
        if (rhs === 0) throw new Error('division by zero');
        value /= rhs;
      } else if (this.match('%')) {
        const rhs = this.parseUnary();
        if (rhs === 0) throw new Error('remainder by zero');
        value %= rhs;
      } else {
        break;
      }
      if (!Number.isFinite(value)) throw new Error('non-finite result');
    }
    return value;
  }

  private parseUnary(): number {
    this.skipWs();
    if (this.match('+')) return this.parseUnary();
    if (this.match('-')) return -this.parseUnary();
    return this.parsePow();
  }

  private parsePow(): number {
    let value = this.parsePrimary();
    this.skipWs();
    if (this.match('^')) {
      const rhs = this.parsePow();
      value = Math.pow(value, rhs);
      if (!Number.isFinite(value)) throw new Error('non-finite result');
    }
    return value;
  }

  private parsePrimary(): number {
    this.skipWs();
    if (this.match('(')) {
      const value = this.parseExpr();
      this.skipWs();
      if (!this.match(')')) {
        throw new Error('missing closing parenthesis');
      }
      this.skipWs();
      return value;
    }
    return this.parseNumber();
  }

  private parseNumber(): number {
    this.skipWs();
    const start = this.i;
    let sawDigit = false;
    let sawDot = false;

    while (this.i < this.n && this.isDigit(this.s[this.i])) {
      this.i++;
      sawDigit = true;
    }

    if (this.i < this.n && this.s[this.i] === '.') {
      sawDot = true;
      this.i++;
      while (this.i < this.n && this.isDigit(this.s[this.i])) {
        this.i++;
        sawDigit = true;
      }
    }

    if (!sawDigit && !sawDot) {
      throw new Error('expected number');
    }

    if (this.i < this.n && (this.s[this.i] === 'e' || this.s[this.i] === 'E')) {
      this.i++;
      if (this.i < this.n && (this.s[this.i] === '+' || this.s[this.i] === '-')) {
        this.i++;
      }
      if (this.i >= this.n || !this.isDigit(this.s[this.i])) {
        throw new Error('invalid exponent');
      }
      while (this.i < this.n && this.isDigit(this.s[this.i])) {
        this.i++;
      }
    }

    const token = this.s.substring(start, this.i);
    const value = Number(token);
    if (!Number.isFinite(value)) {
      throw new Error('non-finite literal');
    }
    return value;
  }

  private skipWs() {
    while (this.i < this.n && /\s/.test(this.s[this.i])) {
      this.i++;
    }
  }

  private match(ch: string): boolean {
    if (this.i < this.n && this.s[this.i] === ch) {
      this.i++;
      return true;
    }
    return false;
  }

  private isDigit(ch: string): boolean {
    return ch >= '0' && ch <= '9';
  }
}

try {
  const p = new Parser(args[2]);
  const result = p.parse();
  const out = Object.is(result, -0) ? 0 : result;
  console.log(String(out));
} catch (err) {
  const msg = err instanceof Error ? err.message : 'parse failure';
  console.error(`error: ${msg}`);
  process.exit(1);
}
