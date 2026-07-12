const NUMBER: RegExp = /(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?/y;

class ParseError extends Error {}

class Parser {
  private position = 0;
  private readonly source: string;

  constructor(source: string) {
    this.source = source;
  }

  private skipSpace(): void {
    while (this.position < this.source.length && this.source.charCodeAt(this.position) < 128 && /\s/.test(this.source[this.position])) this.position++;
  }

  private take(character: string): boolean {
    this.skipSpace();
    if (this.source[this.position] === character) { this.position++; return true; }
    return false;
  }

  parse(): number {
    const result = this.parseAdditive();
    this.skipSpace();
    if (this.position !== this.source.length) throw new ParseError("trailing tokens");
    return result;
  }

  private parseAdditive(): number {
    let result = this.parseMultiplicative();
    while (true) {
      if (this.take("+")) result = this.checked(result + this.parseMultiplicative());
      else if (this.take("-")) result = this.checked(result - this.parseMultiplicative());
      else return result;
    }
  }

  private parseMultiplicative(): number {
    let result = this.parseUnary();
    while (true) {
      if (this.take("*")) result = this.checked(result * this.parseUnary());
      else if (this.take("/")) {
        const right = this.parseUnary();
        if (right === 0) throw new ParseError("division by zero");
        result = this.checked(result / right);
      } else if (this.take("%")) {
        const right = this.parseUnary();
        if (right === 0) throw new ParseError("remainder by zero");
        result = this.checked(result % right);
      } else return result;
    }
  }

  private parseUnary(): number {
    if (this.take("+")) return this.parseUnary();
    if (this.take("-")) return this.checked(-this.parseUnary());
    return this.parsePower();
  }

  private parsePower(): number {
    const result = this.parsePrimary();
    if (this.take("^")) return this.checked(result ** this.parseUnary());
    return result;
  }

  private parsePrimary(): number {
    if (this.take("(")) {
      const result = this.parseAdditive();
      if (!this.take(")")) throw new ParseError("expected ')'");
      return result;
    }
    this.skipSpace();
    NUMBER.lastIndex = this.position;
    const match = NUMBER.exec(this.source);
    if (!match) throw new ParseError("expected number or '('");
    this.position = NUMBER.lastIndex;
    return this.checked(Number(match[0]));
  }

  private checked(value: number): number {
    if (!Number.isFinite(value)) throw new ParseError("non-finite result");
    return value;
  }
}

if (process.argv.length !== 3) {
  console.error("error: expected exactly one expression");
  process.exit(1);
}
try {
  console.log(String(new Parser(process.argv[2]).parse()));
} catch (error) {
  console.error(`error: ${error instanceof Error ? error.message : "calculator failure"}`);
  process.exit(1);
}
