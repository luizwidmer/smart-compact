type CalcFailure = Error;

class Parser {
  private pos = 0;
  private readonly text: string;
  constructor(text: string) { this.text = text; }

  private fail(message: string): never { throw new Error(message); }

  private whitespace(): void {
    while (this.pos < this.text.length && " \t\n\r\v\f".includes(this.text[this.pos])) this.pos++;
  }

  private number(): number {
    this.whitespace();
    const start = this.pos;
    let digits = 0;
    while (this.pos < this.text.length && this.text[this.pos] >= "0" && this.text[this.pos] <= "9") { this.pos++; digits++; }
    if (this.pos < this.text.length && this.text[this.pos] === ".") {
      this.pos++;
      while (this.pos < this.text.length && this.text[this.pos] >= "0" && this.text[this.pos] <= "9") { this.pos++; digits++; }
    }
    if (digits === 0) { this.pos = start; return this.fail("expected number"); }
    if (this.pos < this.text.length && "eE".includes(this.text[this.pos])) {
      this.pos++;
      if (this.pos < this.text.length && "+-".includes(this.text[this.pos])) this.pos++;
      const exponentStart = this.pos;
      while (this.pos < this.text.length && this.text[this.pos] >= "0" && this.text[this.pos] <= "9") this.pos++;
      if (this.pos === exponentStart) return this.fail("malformed exponent");
    }
    const value = Number(this.text.slice(start, this.pos));
    if (!Number.isFinite(value)) return this.fail("non-finite number");
    return value;
  }

  private primary(): number {
    this.whitespace();
    if (this.pos < this.text.length && this.text[this.pos] === "(") {
      this.pos++;
      const value = this.additive();
      this.whitespace();
      if (this.pos >= this.text.length || this.text[this.pos] !== ")") return this.fail("expected closing parenthesis");
      this.pos++;
      return value;
    }
    return this.number();
  }

  private power(): number {
    let value = this.primary();
    this.whitespace();
    if (this.pos < this.text.length && this.text[this.pos] === "^") {
      this.pos++;
      value = Math.pow(value, this.unary());
      if (!Number.isFinite(value)) return this.fail("non-finite result");
    }
    return value;
  }

  private unary(): number {
    this.whitespace();
    if (this.pos < this.text.length && "+-".includes(this.text[this.pos])) {
      const negative = this.text[this.pos] === "-";
      this.pos++;
      const value = this.unary();
      return negative ? -value : value;
    }
    return this.power();
  }

  private multiplicative(): number {
    let value = this.unary();
    while (true) {
      this.whitespace();
      if (this.pos >= this.text.length || !"*/%".includes(this.text[this.pos])) return value;
      const op = this.text[this.pos++];
      const right = this.unary();
      if (right === 0) return this.fail("division by zero");
      if (op === "*") value *= right;
      else if (op === "/") value /= right;
      else value %= right;
      if (!Number.isFinite(value)) return this.fail("non-finite result");
    }
  }

  private additive(): number {
    let value = this.multiplicative();
    while (true) {
      this.whitespace();
      if (this.pos >= this.text.length || !"+-".includes(this.text[this.pos])) return value;
      const op = this.text[this.pos++];
      const right = this.multiplicative();
      value = op === "+" ? value + right : value - right;
      if (!Number.isFinite(value)) return this.fail("non-finite result");
    }
  }

  parse(): number {
    this.whitespace();
    if (this.pos === this.text.length) return this.fail("empty expression");
    const value = this.additive();
    this.whitespace();
    if (this.pos !== this.text.length) return this.fail("trailing tokens");
    return value;
  }
}

try {
  if (process.argv.length !== 3) throw new Error("expected exactly one expression");
  console.log(new Parser(process.argv[2]).parse());
} catch (error) {
  const message = (error as CalcFailure).message || "calculator failure";
  console.error(`error: ${message}`);
  process.exitCode = 1;
}
