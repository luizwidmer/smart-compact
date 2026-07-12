#!/usr/bin/env node
'use strict';

function fail(message) {
  console.error(`error: ${message}`);
  process.exit(1);
}

class Parser {
  constructor(text) {
    this.text = text;
    this.length = text.length;
    this.pos = 0;
  }

  parse() {
    const value = this.parseAddSub();
    this.skipWs();
    if (this.pos !== this.length) {
      fail('trailing input');
    }
    return this.ensureFinite(value);
  }

  skipWs() {
    while (this.pos < this.length && /\s/.test(this.text[this.pos])) {
      this.pos += 1;
    }
  }

  parseAddSub() {
    let value = this.parseMulDivMod();
    while (true) {
      this.skipWs();
      if (this.pos >= this.length) break;
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

  parseMulDivMod() {
    let value = this.parseUnary();
    while (true) {
      this.skipWs();
      if (this.pos >= this.length) break;
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

  parseUnary() {
    this.skipWs();
    if (this.pos >= this.length) fail('malformed expression');
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

  parsePow() {
    let value = this.parsePrimary();
    this.skipWs();
    if (this.pos < this.length && this.text[this.pos] === '^') {
      this.pos += 1;
      const right = this.parsePow();
      value = this.ensureFinite(Math.pow(value, right));
    }
    return value;
  }

  parsePrimary() {
    this.skipWs();
    if (this.pos >= this.length) fail('malformed expression');
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

  parseNumber() {
    this.skipWs();
    if (this.pos >= this.length) fail('malformed expression');
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

  ensureFinite(value) {
    if (!Number.isFinite(value)) {
      fail('non-finite result');
    }
    return value;
  }
}

function main() {
  if (process.argv.length !== 3) {
    fail('expected exactly one argument');
  }
  const parser = new Parser(process.argv[2]);
  const result = parser.parse();
  process.stdout.write(String(result) + '\n');
}

main();
