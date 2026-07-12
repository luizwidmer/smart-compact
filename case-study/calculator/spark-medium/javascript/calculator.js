#!/usr/bin/env node
'use strict';

const expr = process.argv[2];
if (process.argv.length !== 3) {
  console.error('error: expected exactly one expression argument');
  process.exit(1);
}

class Parser {
  constructor(text) {
    this.s = text;
    this.i = 0;
    this.n = text.length;
  }

  parse() {
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

  parseExpr() {
    return this.parseAdd();
  }

  parseAdd() {
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

  parseMul() {
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

  parseUnary() {
    this.skipWs();
    if (this.match('+')) return this.parseUnary();
    if (this.match('-')) return -this.parseUnary();
    return this.parsePow();
  }

  parsePow() {
    let value = this.parsePrimary();
    this.skipWs();
    if (this.match('^')) {
      const rhs = this.parsePow();
      value = Math.pow(value, rhs);
      if (!Number.isFinite(value)) throw new Error('non-finite result');
    }
    return value;
  }

  parsePrimary() {
    this.skipWs();
    if (this.match('(')) {
      const value = this.parseExpr();
      this.skipWs();
      if (!this.match(')')) throw new Error('missing closing parenthesis');
      this.skipWs();
      return value;
    }
    return this.parseNumber();
  }

  parseNumber() {
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

    const token = this.s.slice(start, this.i);
    const value = Number(token);
    if (!Number.isFinite(value)) throw new Error('non-finite literal');
    return value;
  }

  skipWs() {
    while (this.i < this.n && /\s/.test(this.s[this.i])) {
      this.i++;
    }
  }

  match(ch) {
    if (this.i < this.n && this.s[this.i] === ch) {
      this.i++;
      return true;
    }
    return false;
  }

  isDigit(ch) {
    return ch >= '0' && ch <= '9';
  }
}

try {
  const p = new Parser(expr);
  const result = p.parse();
  const out = Object.is(result, -0) ? 0 : result;
  console.log(String(out));
} catch (err) {
  console.error(`error: ${err.message}`);
  process.exit(1);
}
