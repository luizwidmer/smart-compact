#!/usr/bin/env node

function fail(message: string): never {
  console.error(`error: ${message}`);
  process.exit(1);
}

if (process.argv.length !== 3) {
  fail('expected one expression argument');
}

class Parser {
  private readonly text: string;
  private pos = 0;
  private readonly len: number;

  constructor(text: string) {
    this.text = text;
    this.len = text.length;
  }

  parse(): number {
    const value = this.parseExpression();
    this.skipWs();
    if (this.pos !== this.len) fail('unexpected trailing token');
    if (!Number.isFinite(value)) fail('result is not finite');
    return value;
  }

  private parseExpression(): number {
    let value = this.parseTerm();
    while (true) {
      this.skipWs();
      if (this.match('+')) {
        value = this.ensureFinite(value + this.parseTerm());
      } else if (this.match('-')) {
        value = this.ensureFinite(value - this.parseTerm());
      } else {
        return this.ensureFinite(value);
      }
    }
  }

  private parseTerm(): number {
    let value = this.parsePower();
    while (true) {
      this.skipWs();
      if (this.match('*')) {
        value = this.ensureFinite(value * this.parsePower());
      } else if (this.match('/')) {
        const rhs = this.parsePower();
        if (rhs === 0) fail('division by zero');
        value = this.ensureFinite(value / rhs);
      } else if (this.match('%')) {
        const rhs = this.parsePower();
        if (rhs === 0) fail('remainder by zero');
        value = this.ensureFinite(value % rhs);
      } else {
        return this.ensureFinite(value);
      }
    }
  }

  private parsePower(): number {
    const left = this.parseUnary();
    this.skipWs();
    if (this.match('^')) {
      const right = this.parsePower();
      const value = Math.pow(left, right);
      return this.ensureFinite(value);
    }
    return this.ensureFinite(left);
  }

  private parseUnary(): number {
    this.skipWs();
    if (this.match('+')) {
      return this.parseUnary();
    }
    if (this.match('-')) {
      return this.ensureFinite(-this.parseUnary());
    }
    return this.parsePrimary();
  }

  private parsePrimary(): number {
    this.skipWs();
    if (this.match('(')) {
      const value = this.parseExpression();
      this.skipWs();
      if (!this.match(')')) fail('missing closing parenthesis');
      return this.ensureFinite(value);
    }
    return this.parseNumber();
  }

  private parseNumber(): number {
    this.skipWs();
    const start = this.pos;

    if (this.pos >= this.len) fail('expected number');

    if (this.peek() === '.') {
      this.pos++;
      if (this.pos >= this.len || !this.isDigit(this.peek())) fail('invalid number');
      while (this.pos < this.len && this.isDigit(this.peek())) this.pos++;
    } else if (this.isDigit(this.peek())) {
      while (this.pos < this.len && this.isDigit(this.peek())) this.pos++;
      if (this.peek() === '.') {
        this.pos++;
        while (this.pos < this.len && this.isDigit(this.peek())) this.pos++;
      }
    } else {
      fail('invalid number');
    }

    if (this.peek() === 'e' || this.peek() === 'E') {
      this.pos++;
      if (this.peek() === '+' || this.peek() === '-') this.pos++;
      if (this.pos >= this.len || !this.isDigit(this.peek())) fail('invalid scientific notation');
      while (this.pos < this.len && this.isDigit(this.peek())) this.pos++;
    }

    const token = this.text.slice(start, this.pos);
    const value = Number(token);
    return this.ensureFinite(value);
  }

  private ensureFinite(value: number): number {
    if (!Number.isFinite(value)) fail('result is not finite');
    return value;
  }

  private skipWs(): void {
    while (this.pos < this.len && this.isWhitespace(this.text[this.pos])) this.pos++;
  }

  private match(ch: string): boolean {
    if (this.pos < this.len && this.text[this.pos] === ch) {
      this.pos++;
      return true;
    }
    return false;
  }

  private peek(): string {
    return this.text[this.pos];
  }

  private isDigit(ch: string): boolean {
    return ch >= '0' && ch <= '9';
  }

  private isWhitespace(ch: string): boolean {
    return ch === ' ' || ch === '\t' || ch === '\n' || ch === '\r' || ch === '\f' || ch === '\v';
  }
}

const parser = new Parser(process.argv[2]);
console.log(String(parser.parse()));
