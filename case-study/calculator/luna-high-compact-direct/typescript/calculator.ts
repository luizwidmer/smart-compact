const NUMBER: RegExp = /(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?/y;
const SPACE: Set<string> = new Set([" ", "\t", "\n", "\r", "\v", "\f"]);

class ParseError extends Error {}

class Parser {
  private pos: number = 0;
  private readonly text: string;

  constructor(text: string) {
    this.text = text;
  }

  private skipSpace(): void {
    while (this.pos < this.text.length && SPACE.has(this.text[this.pos])) this.pos++;
  }

  private take(token: string): boolean {
    this.skipSpace();
    if (this.text.startsWith(token, this.pos)) {
      this.pos += token.length;
      return true;
    }
    return false;
  }

  private expression(): number {
    let value = this.term();
    for (;;) {
      if (this.take("+")) value = this.checked(value + this.term());
      else if (this.take("-")) value = this.checked(value - this.term());
      else return value;
    }
  }

  private term(): number {
    let value = this.unary();
    for (;;) {
      if (this.take("*")) value = this.checked(value * this.unary());
      else if (this.take("/")) {
        const right = this.unary();
        if (right === 0) throw new ParseError("division by zero");
        value = this.checked(value / right);
      } else if (this.take("%")) {
        const right = this.unary();
        if (right === 0) throw new ParseError("remainder by zero");
        value = this.checked(value % right);
      } else return value;
    }
  }

  private unary(): number {
    if (this.take("+")) return this.unary();
    if (this.take("-")) return this.checked(-this.unary());
    return this.power();
  }

  private power(): number {
    const value = this.primary();
    if (!this.take("^")) return value;
    return this.checked(Math.pow(value, this.unary()));
  }

  private primary(): number {
    if (this.take("(")) {
      const value = this.expression();
      if (!this.take(")")) throw new ParseError("missing closing parenthesis");
      return value;
    }
    this.skipSpace();
    NUMBER.lastIndex = this.pos;
    const match: RegExpExecArray | null = NUMBER.exec(this.text);
    if (match === null) throw new ParseError("expected number or parenthesis");
    this.pos = NUMBER.lastIndex;
    return this.checked(Number(match[0]));
  }

  private checked(value: number): number {
    if (!Number.isFinite(value)) throw new ParseError("non-finite result");
    return value;
  }

  parse(): number {
    const value = this.expression();
    this.skipSpace();
    if (this.pos !== this.text.length) throw new ParseError("trailing tokens");
    return this.checked(value);
  }
}

if (process.argv.length !== 3) {
  console.error("error: expected exactly one expression argument");
  process.exitCode = 2;
} else {
  try {
    console.log(String(new Parser(process.argv[2]).parse()));
  } catch (_) {
    console.error("error: invalid expression");
    process.exitCode = 1;
  }
}
