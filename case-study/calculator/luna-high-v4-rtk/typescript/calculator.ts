const NUMBER: RegExp = /(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?/y;
const WHITESPACE: string = " \t\n\r\v\f";

class Parser {
  private pos: number = 0;
  private readonly text: string;

  constructor(text: string) {
    this.text = text;
  }

  private error(message: string): never {
    throw new Error(message);
  }

  private skipWhitespace(): void {
    while (this.pos < this.text.length && WHITESPACE.includes(this.text[this.pos])) {
      this.pos += 1;
    }
  }

  private match(token: string): boolean {
    this.skipWhitespace();
    if (this.text.startsWith(token, this.pos)) {
      this.pos += token.length;
      return true;
    }
    return false;
  }

  private parseNumber(): number {
    this.skipWhitespace();
    NUMBER.lastIndex = this.pos;
    const match: RegExpExecArray | null = NUMBER.exec(this.text);
    if (match === null) this.error("expected number");
    this.pos = NUMBER.lastIndex;
    const value: number = Number(match[0]);
    if (!Number.isFinite(value)) this.error("non-finite number");
    return value;
  }

  private parsePrimary(): number {
    if (this.match("(")) {
      const value: number = this.parseExpression();
      if (!this.match(")")) this.error("expected ')' ");
      return value;
    }
    return this.parseNumber();
  }

  private parsePower(): number {
    const value: number = this.parsePrimary();
    if (this.match("^")) {
      const result: number = value ** this.parseUnary();
      if (!Number.isFinite(result)) this.error("non-finite result");
      return result;
    }
    return value;
  }

  private parseUnary(): number {
    if (this.match("+")) return this.parseUnary();
    if (this.match("-")) {
      const result: number = -this.parseUnary();
      if (!Number.isFinite(result)) this.error("non-finite result");
      return result;
    }
    return this.parsePower();
  }

  private parseMultiplicative(): number {
    let value: number = this.parseUnary();
    while (true) {
      if (this.match("*")) value *= this.parseUnary();
      else if (this.match("/")) {
        const divisor: number = this.parseUnary();
        if (divisor === 0) this.error("division by zero");
        value /= divisor;
      } else if (this.match("%")) {
        const divisor: number = this.parseUnary();
        if (divisor === 0) this.error("remainder by zero");
        value %= divisor;
      } else break;
      if (!Number.isFinite(value)) this.error("non-finite result");
    }
    return value;
  }

  private parseExpression(): number {
    let value: number = this.parseMultiplicative();
    while (true) {
      if (this.match("+")) value += this.parseMultiplicative();
      else if (this.match("-")) value -= this.parseMultiplicative();
      else break;
      if (!Number.isFinite(value)) this.error("non-finite result");
    }
    return value;
  }

  parse(): number {
    const value: number = this.parseExpression();
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
} catch (error: unknown) {
  const message: string = error instanceof Error ? error.message : String(error);
  console.error(`error: ${message}`);
  process.exit(1);
}
