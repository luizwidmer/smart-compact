class ParseError extends Error {}

class Parser {
  constructor(text) {
    this.text = text;
    this.pos = 0;
  }

  isSpace(code) {
    return code === 32 || code === 9 || code === 10 || code === 11 || code === 12 || code === 13;
  }

  skipSpace() {
    while (this.pos < this.text.length && this.isSpace(this.text.charCodeAt(this.pos))) this.pos++;
  }

  checked(value) {
    if (!Number.isFinite(value)) throw new ParseError("non-finite result");
    return value;
  }

  parse() {
    const value = this.parseAdditive();
    this.skipSpace();
    if (this.pos !== this.text.length) throw new ParseError("trailing tokens");
    return this.checked(value);
  }

  parseAdditive() {
    let value = this.parseMultiplicative();
    while (true) {
      this.skipSpace();
      if (this.pos >= this.text.length || !"+-".includes(this.text[this.pos])) return value;
      const op = this.text[this.pos++];
      const right = this.parseMultiplicative();
      value = this.checked(op === "+" ? value + right : value - right);
    }
  }

  parseMultiplicative() {
    let value = this.parseUnary();
    while (true) {
      this.skipSpace();
      if (this.pos >= this.text.length || !"*/%".includes(this.text[this.pos])) return value;
      const op = this.text[this.pos++];
      const right = this.parseUnary();
      if (right === 0) throw new ParseError("division by zero");
      if (op === "*") value = this.checked(value * right);
      else if (op === "/") value = this.checked(value / right);
      else value = this.checked(value % right);
    }
  }

  parseUnary() {
    this.skipSpace();
    if (this.pos < this.text.length && "+-".includes(this.text[this.pos])) {
      const op = this.text[this.pos++];
      const value = this.parseUnary();
      return this.checked(op === "+" ? value : -value);
    }
    return this.parsePower();
  }

  parsePower() {
    const value = this.parsePrimary();
    this.skipSpace();
    if (this.pos < this.text.length && this.text[this.pos] === "^") {
      this.pos++;
      return this.checked(Math.pow(value, this.parseUnary()));
    }
    return value;
  }

  parsePrimary() {
    this.skipSpace();
    if (this.pos >= this.text.length) throw new ParseError("expected expression");
    if (this.text[this.pos] === "(") {
      this.pos++;
      const value = this.parseAdditive();
      this.skipSpace();
      if (this.pos >= this.text.length || this.text[this.pos] !== ")") throw new ParseError("expected closing parenthesis");
      this.pos++;
      return value;
    }
    return this.parseNumber();
  }

  parseNumber() {
    const start = this.pos;
    let digits = 0;
    while (this.pos < this.text.length && this.text.charCodeAt(this.pos) >= 48 && this.text.charCodeAt(this.pos) <= 57) { this.pos++; digits++; }
    if (this.pos < this.text.length && this.text[this.pos] === ".") {
      this.pos++;
      while (this.pos < this.text.length && this.text.charCodeAt(this.pos) >= 48 && this.text.charCodeAt(this.pos) <= 57) { this.pos++; digits++; }
    }
    if (digits === 0) throw new ParseError("expected number");
    if (this.pos < this.text.length && "eE".includes(this.text[this.pos])) {
      this.pos++;
      if (this.pos < this.text.length && "+-".includes(this.text[this.pos])) this.pos++;
      const exponentStart = this.pos;
      while (this.pos < this.text.length && this.text.charCodeAt(this.pos) >= 48 && this.text.charCodeAt(this.pos) <= 57) this.pos++;
      if (this.pos === exponentStart) throw new ParseError("invalid exponent");
    }
    return this.checked(Number(this.text.slice(start, this.pos)));
  }
}

try {
  if (process.argv.length !== 3) throw new ParseError("expected exactly one argument");
  console.log(String(new Parser(process.argv[2]).parse()));
} catch (error) {
  process.stderr.write(`error: ${error.message}\n`);
  process.exitCode = 1;
}
