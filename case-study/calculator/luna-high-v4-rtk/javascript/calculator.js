const NUMBER = /(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?/y;
const WHITESPACE = " \t\n\r\v\f";

class Parser {
  constructor(text) {
    this.text = text;
    this.pos = 0;
  }

  error(message) {
    throw new Error(message);
  }

  skipWhitespace() {
    while (this.pos < this.text.length && WHITESPACE.includes(this.text[this.pos])) {
      this.pos += 1;
    }
  }

  match(token) {
    this.skipWhitespace();
    if (this.text.startsWith(token, this.pos)) {
      this.pos += token.length;
      return true;
    }
    return false;
  }

  parseNumber() {
    this.skipWhitespace();
    NUMBER.lastIndex = this.pos;
    const match = NUMBER.exec(this.text);
    if (match === null) this.error("expected number");
    this.pos = NUMBER.lastIndex;
    const value = Number(match[0]);
    if (!Number.isFinite(value)) this.error("non-finite number");
    return value;
  }

  parsePrimary() {
    if (this.match("(")) {
      const value = this.parseExpression();
      if (!this.match(")")) this.error("expected ')' ");
      return value;
    }
    return this.parseNumber();
  }

  parsePower() {
    const value = this.parsePrimary();
    if (this.match("^")) {
      const result = value ** this.parseUnary();
      if (!Number.isFinite(result)) this.error("non-finite result");
      return result;
    }
    return value;
  }

  parseUnary() {
    if (this.match("+")) return this.parseUnary();
    if (this.match("-")) {
      const result = -this.parseUnary();
      if (!Number.isFinite(result)) this.error("non-finite result");
      return result;
    }
    return this.parsePower();
  }

  parseMultiplicative() {
    let value = this.parseUnary();
    while (true) {
      if (this.match("*")) value *= this.parseUnary();
      else if (this.match("/")) {
        const divisor = this.parseUnary();
        if (divisor === 0) this.error("division by zero");
        value /= divisor;
      } else if (this.match("%")) {
        const divisor = this.parseUnary();
        if (divisor === 0) this.error("remainder by zero");
        value %= divisor;
      } else break;
      if (!Number.isFinite(value)) this.error("non-finite result");
    }
    return value;
  }

  parseExpression() {
    let value = this.parseMultiplicative();
    while (true) {
      if (this.match("+")) value += this.parseMultiplicative();
      else if (this.match("-")) value -= this.parseMultiplicative();
      else break;
      if (!Number.isFinite(value)) this.error("non-finite result");
    }
    return value;
  }

  parse() {
    const value = this.parseExpression();
    this.skipWhitespace();
    if (this.pos !== this.text.length) this.error("trailing tokens");
    return value;
  }
}

if (process.argv.length !== 3) {
  console.error("error: expected exactly one expression argument");
  process.exit(1);
}

try {
  console.log(String(new Parser(process.argv[2]).parse()));
} catch (error) {
  console.error(`error: ${error.message}`);
  process.exit(1);
}
