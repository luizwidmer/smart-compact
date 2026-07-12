#!/usr/bin/env node

class Parser {
  constructor(s) {
    this.s = s;
    this.i = 0;
    this.n = s.length;
  }

  skipWs() {
    while (this.i < this.n && /\s/.test(this.s[this.i])) this.i++;
  }

  parseNumber() {
    this.skipWs();
    const start = this.i;
    let hasDigit = false;

    if (this.s[this.i] === '.') {
      this.i++;
      while (this.i < this.n && /[0-9]/.test(this.s[this.i])) {
        this.i++;
        hasDigit = true;
      }
    } else {
      while (this.i < this.n && /[0-9]/.test(this.s[this.i])) {
        this.i++;
        hasDigit = true;
      }
      if (this.s[this.i] === '.') {
        this.i++;
        while (this.i < this.n && /[0-9]/.test(this.s[this.i])) {
          this.i++;
          hasDigit = true;
        }
      }
    }

    if (!hasDigit) throw new Error('invalid number');

    if (this.s[this.i] === 'e' || this.s[this.i] === 'E') {
      this.i++;
      if (this.s[this.i] === '+' || this.s[this.i] === '-') this.i++;
      if (this.i >= this.n || !/[0-9]/.test(this.s[this.i])) throw new Error('invalid exponent');
      while (this.i < this.n && /[0-9]/.test(this.s[this.i])) this.i++;
    }

    const token = this.s.slice(start, this.i);
    const value = Number(token);
    if (!Number.isFinite(value)) throw new Error('non-finite number');
    return value;
  }

  parseExpr() {
    let value = this.parseTerm();
    while (true) {
      this.skipWs();
      if (this.i >= this.n) return value;
      const ch = this.s[this.i];
      if (ch !== '+' && ch !== '-') return value;
      this.i++;
      const rhs = this.parseTerm();
      value = ch === '+' ? value + rhs : value - rhs;
    }
  }

  parseTerm() {
    let value = this.parsePower();
    while (true) {
      this.skipWs();
      if (this.i >= this.n) return value;
      const ch = this.s[this.i];
      if (ch !== '*' && ch !== '/' && ch !== '%') return value;
      this.i++;
      const rhs = this.parsePower();
      if (ch === '*') value *= rhs;
      else if (ch === '/') {
        if (rhs === 0) throw new Error('division by zero');
        value /= rhs;
      } else {
        if (rhs === 0) throw new Error('remainder by zero');
        value %= rhs;
      }
      if (!Number.isFinite(value)) throw new Error('non-finite result');
    }
  }

  parsePower() {
    let value = this.parseUnary();
    this.skipWs();
    if (this.i >= this.n || this.s[this.i] !== '^') return value;
    this.i++;
    const rhs = this.parsePower();
    value = Math.pow(value, rhs);
    if (!Number.isFinite(value)) throw new Error('non-finite result');
    return value;
  }

  parseUnary() {
    this.skipWs();
    if (this.i < this.n && (this.s[this.i] === '+' || this.s[this.i] === '-')) {
      const op = this.s[this.i];
      this.i++;
      const value = this.parseUnary();
      return op === '-' ? -value : value;
    }
    return this.parsePrimary();
  }

  parsePrimary() {
    this.skipWs();
    if (this.i >= this.n) throw new Error('unexpected end');
    if (this.s[this.i] === '(') {
      this.i++;
      const value = this.parseExpr();
      this.skipWs();
      if (this.s[this.i] !== ')') throw new Error('missing )');
      this.i++;
      return value;
    }
    return this.parseNumber();
  }
}

function evaluate(expr) {
  const p = new Parser(expr);
  p.skipWs();
  if (p.i >= p.n) throw new Error('empty expression');
  const value = p.parseExpr();
  p.skipWs();
  if (p.i !== p.n) throw new Error('trailing token');
  if (!Number.isFinite(value)) throw new Error('non-finite result');
  return value;
}

function main() {
  const args = process.argv.slice(2);
  if (args.length !== 1) {
    console.error('error: expected exactly one expression');
    process.exit(1);
  }
  try {
    const value = evaluate(args[0]);
    process.stdout.write(String(value) + '\n');
  } catch (err) {
    console.error('error: ' + String(err.message || err));
    process.exit(2);
  }
}

main();
