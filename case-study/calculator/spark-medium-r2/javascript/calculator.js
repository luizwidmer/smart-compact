#!/usr/bin/env node

'use strict';

function fail(message) {
  console.error(`error: ${message}`);
  process.exit(1);
}

if (process.argv.length !== 3) {
  fail('expected one expression argument');
}

class Parser {
  constructor(text) {
    this.text = text;
    this.pos = 0;
    this.len = text.length;
  }

  parse() {
    const value = this.parseExpression();
    this.skipWs();
    if (this.pos !== this.len) fail('unexpected trailing token');
    if (!Number.isFinite(value)) fail('result is not finite');
    return value;
  }

  parseExpression() {
    let value = this.parseTerm();
    while (true) {
      this.skipWs();
      if (this.match('+')) {
        value += this.parseTerm();
      } else if (this.match('-')) {
        value -= this.parseTerm();
      } else {
        if (!Number.isFinite(value)) fail('result is not finite');
        return value;
      }
    }
  }

  parseTerm() {
    let value = this.parsePower();
    while (true) {
      this.skipWs();
      if (this.match('*')) {
        value *= this.parsePower();
      } else if (this.match('/')) {
        const rhs = this.parsePower();
        if (rhs === 0) fail('division by zero');
        value /= rhs;
      } else if (this.match('%')) {
        const rhs = this.parsePower();
        if (rhs === 0) fail('remainder by zero');
        value %= rhs;
      } else {
        if (!Number.isFinite(value)) fail('result is not finite');
        return value;
      }
      if (!Number.isFinite(value)) fail('result is not finite');
    }
  }

  parsePower() {
    const left = this.parseUnary();
    this.skipWs();
    if (this.match('^')) {
      const right = this.parsePower();
      const value = Math.pow(left, right);
      if (!Number.isFinite(value)) fail('result is not finite');
      return value;
    }
    return left;
  }

  parseUnary() {
    this.skipWs();
    if (this.match('+')) return this.parseUnary();
    if (this.match('-')) return -this.parseUnary();
    return this.parsePrimary();
  }

  parsePrimary() {
    this.skipWs();
    if (this.match('(')) {
      const value = this.parseExpression();
      this.skipWs();
      if (!this.match(')')) fail('missing closing parenthesis');
      return value;
    }
    return this.parseNumber();
  }

  parseNumber() {
    this.skipWs();
    const start = this.pos;

    if (this.pos >= this.len) fail('expected number');

    let hasDigit = false;
    let hasDecimal = false;

    if (this.peek() === '.') {
      hasDecimal = true;
      this.pos++;
      if (this.pos >= this.len || !isDigit(this.peek())) fail('invalid number');
      while (this.pos < this.len && isDigit(this.peek())) {
        this.pos++;
        hasDigit = true;
      }
    } else if (isDigit(this.peek())) {
      hasDigit = true;
      while (this.pos < this.len && isDigit(this.peek())) {
        this.pos++;
      }
      if (this.peek() === '.') {
        hasDecimal = true;
        this.pos++;
        while (this.pos < this.len && isDigit(this.peek())) {
          this.pos++;
        }
      }
    } else {
      fail('invalid number');
    }

    if (this.pos < this.len && (this.peek() === 'e' || this.peek() === 'E')) {
      this.pos++;
      if (this.peek() === '+' || this.peek() === '-') this.pos++;
      if (this.pos >= this.len || !isDigit(this.peek())) fail('invalid scientific notation');
      while (this.pos < this.len && isDigit(this.peek())) {
        this.pos++;
      }
    }

    const token = this.text.slice(start, this.pos);
    const value = Number(token);
    if (!Number.isFinite(value)) fail('number is not finite');
    return value;
  }

  skipWs() {
    while (this.pos < this.len && isWhitespace(this.text[this.pos])) this.pos++;
  }

  match(ch) {
    if (this.pos < this.len && this.text[this.pos] === ch) {
      this.pos++;
      return true;
    }
    return false;
  }

  peek() {
    return this.text[this.pos];
  }
}

function isDigit(ch) {
  return ch >= '0' && ch <= '9';
}

function isWhitespace(ch) {
  return ch === ' ' || ch === '\t' || ch === '\n' || ch === '\r' || ch === '\f' || ch === '\v';
}

const parser = new Parser(process.argv[2]);
const value = parser.parse();
console.log(String(value));
