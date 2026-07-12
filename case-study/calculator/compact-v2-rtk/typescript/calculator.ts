class Parser {
  private text: string;
  private pos: number;

  constructor(text: string) { this.text = text; this.pos = 0; }

  private skipSpace(): void {
    while (this.pos < this.text.length && [9, 10, 11, 12, 13, 32].includes(this.text.charCodeAt(this.pos))) this.pos++;
  }

  private take(token: string): boolean {
    this.skipSpace();
    if (this.text[this.pos] === token) { this.pos++; return true; }
    return false;
  }

  parse(): number {
    const value = this.expression();
    this.skipSpace();
    if (this.pos !== this.text.length) throw new Error('unexpected token');
    return value;
  }

  private expression(): number {
    let value = this.term();
    while (true) {
      if (this.take('+')) value = checked(value + this.term());
      else if (this.take('-')) value = checked(value - this.term());
      else return value;
    }
  }

  private term(): number {
    let value = this.unary();
    while (true) {
      if (this.take('*')) value = checked(value * this.unary());
      else if (this.take('/')) {
        const rhs = this.unary();
        if (rhs === 0) throw new Error('division by zero');
        value = checked(value / rhs);
      } else if (this.take('%')) {
        const rhs = this.unary();
        if (rhs === 0) throw new Error('remainder by zero');
        value = checked(value % rhs);
      } else return value;
    }
  }

  private unary(): number {
    if (this.take('+')) return this.unary();
    if (this.take('-')) return checked(-this.unary());
    return this.power();
  }

  private power(): number {
    let value = this.primary();
    if (this.take('^')) value = checked(Math.pow(value, this.unary()));
    return value;
  }

  private primary(): number {
    if (this.take('(')) {
      const value = this.expression();
      if (!this.take(')')) throw new Error('missing closing parenthesis');
      return value;
    }
    return this.number();
  }

  private number(): number {
    this.skipSpace();
    const start = this.pos;
    let digits = 0;
    while (isDigit(this.text.charCodeAt(this.pos))) { this.pos++; digits++; }
    if (this.text[this.pos] === '.') {
      this.pos++;
      while (isDigit(this.text.charCodeAt(this.pos))) { this.pos++; digits++; }
    }
    if (digits === 0) throw new Error('expected number');
    if (this.text[this.pos] === 'e' || this.text[this.pos] === 'E') {
      this.pos++;
      if (this.text[this.pos] === '+' || this.text[this.pos] === '-') this.pos++;
      const exponent = this.pos;
      while (isDigit(this.text.charCodeAt(this.pos))) this.pos++;
      if (this.pos === exponent) throw new Error('malformed exponent');
    }
    return checked(Number(this.text.slice(start, this.pos)));
  }
}

function isDigit(code: number): boolean { return code >= 48 && code <= 57; }
function checked(value: number): number {
  if (!Number.isFinite(value)) throw new Error('non-finite result');
  return value;
}

try {
  if (process.argv.length !== 3) throw new Error('expected exactly one expression');
  console.log(String(new Parser(process.argv[2]).parse()));
} catch (error: unknown) {
  const message = error instanceof Error ? error.message : 'invalid expression';
  console.error(`error: ${message}`);
  process.exit(1);
}
