#!/usr/bin/env node
'use strict';

function fail(message: string): never {
  console.error(`error: ${message}`);
  process.exit(1);
}

class Parser {
  private readonly text: string;
  private readonly length: number;
  private pos = 0;

  constructor(text: string) {
    this.text = text;
    this.length = text.length;
  }

  parse(): number {
    const value = this.parseAddSub();
    this.skipWs();
    if (this.pos !== this.length) {
      fail('trailing input');
    }
    return this.ensureFinite(value);
  }

  private skipWs(): void {
    while (this.pos < this.length && /\s/.test(this.text[this.pos])) {
      this.pos += 1;
    }
  }

  private parseAddSub(): number {
    let value = this.parseMulDivMod();
    while (true) {
      this.skipWs();
      if (this.pos >= this.length) {
        break;
      }
      const ch = this.text[this.pos];
      if (ch === '+') {
        this.pos += 1;
        const right = this.parseMulDivMod();
        value = this.ensureFinite(value + right);
      } else if (ch === '-') {
        this.pos += 1;
        const right = this.parseMulDivMod();
        value = this.ensureFinite(value - right);
      } else {
        break;
      }
    }
    return value;
  }

  private parseMulDivMod(): number {
    let value = this.parseUnary();
    while (true) {
      this.skipWs();
      if (this.pos >= this.length) {
        break;
      }
      const ch = this.text[this.pos];
      if (ch === '*') {
        this.pos += 1;
        const right = this.parseUnary();
        value = this.ensureFinite(value * right);
      } else if (ch === '/') {
        this.pos += 1;
        const right = this.parseUnary();
        if (right === 0) {
          fail('division by zero');
        }
        value = this.ensureFinite(value / right);
      } else if (ch === '%') {
        this.pos += 1;
        const right = this.parseUnary();
        if (right === 0) {
          fail('remainder by zero');
        }
        value = this.ensureFinite(value % right);
      } else {
        break;
      }
    }
    return value;
  }

  private parseUnary(): number {
    this.skipWs();
    if (this.pos >= this.length) {
      fail('malformed expression');
    }
    const ch = this.text[this.pos];
    if (ch === '+') {
      this.pos += 1;
      return this.parseUnary();
    }
    if (ch === '-') {
      this.pos += 1;
      return this.ensureFinite(-this.parseUnary());
    }
    return this.parsePow();
  }

  private parsePow(): number {
    let value = this.parsePrimary();
    this.skipWs();
    if (this.pos < this.length && this.text[this.pos] === '^') {
      this.pos += 1;
      const right = this.parsePow();
      value = this.ensureFinite(Math.pow(value, right));
    }
    return value;
  }

  private parsePrimary(): number {
    this.skipWs();
    if (this.pos >= this.length) {
      fail('malformed expression');
    }
    const ch = this.text[this.pos];
    if (ch === '(') {
      this.pos += 1;
      const value = this.parseAddSub();
      this.skipWs();
      if (this.pos >= this.length || this.text[this.pos] !== ')') {
        fail('missing closing parenthesis');
      }
      this.pos += 1;
      return value;
    }
    return this.parseNumber();
  }

  private parseNumber(): number {
    this.skipWs();
    if (this.pos >= this.length) {
      fail('malformed expression');
    }
    const rest = this.text.slice(this.pos);
    const match = rest.match(/^(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?/);
    if (!match) {
      fail('invalid token');
    }
    const token = match[0];
    this.pos += token.length;
    const value = Number(token);
    if (!Number.isFinite(value)) {
      fail('non-finite number');
    }
    return this.ensureFinite(value);
  }

  private ensureFinite(value: number): number {
    if (!Number.isFinite(value)) {
      fail('non-finite result');
    }
    return value;
  }
}

function main(): void {
  if (process.argv.length !== 3) {
    fail('expected exactly one argument');
  }
  const parser = new Parser(process.argv[2]);
  const result = parser.parse();
  process.stdout.write(String(result) + '\n');
}

main();
