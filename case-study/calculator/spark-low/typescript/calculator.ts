#!/usr/bin/env node

class Parser {
  private s: string;
  private i = 0;
  private n: number;

  constructor(s: string) {
    this.s = s;
    this.n = s.length;
  }

  private skipWs(): void {
    while (this.i < this.n && /\s/.test(this.s[this.i])) this.i++;
  }

  private parseNumber(): number {
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

    if (!hasDigit) {
      throw new Error('invalid number');
    }

    if (this.s[this.i] === 'e' || this.s[this.i] === 'E') {
      this.i++;
      if (this.s[this.i] === '+' || this.s[this.i] === '-') this.i++;
      if (this.i >= this.n || !/[0-9]/.test(this.s[this.i])) {
        throw new Error('invalid exponent');
      }
      while (this.i < this.n && /[0-9]/.test(this.s[this.i])) this.i++;
    }

    const value = Number(this.s.slice(start, this.i));
    if (!Number.isFinite(value)) throw new Error('non-finite number');
    return value;
  }

  private parsePrimary(): number {
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

  private parseUnary(): number {
    this.skipWs();
    if (this.i < this.n && (this.s[this.i] === '+' || this.s[this.i] === '-')) {
      const op = this.s[this.i];
      this.i++;
      const value = this.parseUnary();
      return op === '-' ? -value : value;
    }
    return this.parsePrimary();
  }

  private parsePower(): number {
    let value = this.parseUnary();
    this.skipWs();
    if (this.i >= this.n || this.s[this.i] !== '^') return value;
    this.i++;
    const rhs = this.parsePower();
    value = Math.pow(value, rhs);
    if (!Number.isFinite(value)) throw new Error('non-finite result');
    return value;
  }

  private parseTerm(): number {
    let value = this.parsePower();
    while (true) {
      this.skipWs();
      if (this.i >= this.n) return value;
      const op = this.s[this.i];
      if (op !== '*' && op !== '/' && op !== '%') return value;
      this.i++;
      const rhs = this.parsePower();
      if (op === '*') value *= rhs;
      else if (op === '/') {
        if (rhs === 0) throw new Error('division by zero');
        value /= rhs;
      } else {
        if (rhs === 0) throw new Error('remainder by zero');
        value %= rhs;
      }
      if (!Number.isFinite(value)) throw new Error('non-finite result');
    }
  }

  private parseExpr(): number {
    let value = this.parseTerm();
    while (true) {
      this.skipWs();
      if (this.i >= this.n) return value;
      const op = this.s[this.i];
      if (op !== '+' && op !== '-') return value;
      this.i++;
      const rhs = this.parseTerm();
      value = op === '+' ? value + rhs : value - rhs;
    }
  }

  public parse(): number {
    this.skipWs();
    if (this.i >= this.n) throw new Error('empty expression');
    const value = this.parseExpr();
    this.skipWs();
    if (this.i !== this.n) throw new Error('trailing token');
    if (!Number.isFinite(value)) throw new Error('non-finite result');
    return value;
  }
}

const args = process.argv.slice(2);
if (args.length !== 1) {
  console.error('error: expected exactly one expression');
  process.exit(1);
}

try {
  const value = new Parser(args[0]).parse();
  process.stdout.write(String(value) + '\n');
} catch (e: any) {
  const msg = e instanceof Error ? e.message : String(e);
  console.error('error: ' + msg);
  process.exit(2);
}
