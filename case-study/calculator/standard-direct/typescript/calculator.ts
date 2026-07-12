class CalculatorError extends Error {}

class Parser {
  private position = 0;
  private readonly text: string;

  constructor(text: string) { this.text = text; }

  private skipSpace(): void {
    while (this.position < this.text.length && " \t\n\r\v\f".includes(this.text[this.position])) this.position++;
  }

  private consume(token: string): boolean {
    this.skipSpace();
    if (this.text[this.position] === token) { this.position++; return true; }
    return false;
  }

  private finite(value: number): number {
    if (!Number.isFinite(value)) throw new CalculatorError("non-finite result");
    return value;
  }

  parse(): number {
    const value = this.additive();
    this.skipSpace();
    if (this.position !== this.text.length) throw new CalculatorError("unexpected trailing input");
    return value;
  }

  private additive(): number {
    let value = this.multiplicative();
    while (true) {
      if (this.consume("+")) value = this.finite(value + this.multiplicative());
      else if (this.consume("-")) value = this.finite(value - this.multiplicative());
      else return value;
    }
  }

  private multiplicative(): number {
    let value = this.unary();
    while (true) {
      if (this.consume("*")) value = this.finite(value * this.unary());
      else if (this.consume("/")) {
        const divisor = this.unary();
        if (divisor === 0) throw new CalculatorError("division by zero");
        value = this.finite(value / divisor);
      } else if (this.consume("%")) {
        const divisor = this.unary();
        if (divisor === 0) throw new CalculatorError("remainder by zero");
        value = this.finite(value % divisor);
      } else return value;
    }
  }

  private unary(): number {
    if (this.consume("+")) return this.unary();
    if (this.consume("-")) return this.finite(-this.unary());
    return this.power();
  }

  private power(): number {
    let value = this.primary();
    if (this.consume("^")) value = this.finite(Math.pow(value, this.unary()));
    return value;
  }

  private primary(): number {
    if (this.consume("(")) {
      const value = this.additive();
      if (!this.consume(")")) throw new CalculatorError("expected closing parenthesis");
      return value;
    }
    return this.number();
  }

  private number(): number {
    this.skipSpace();
    const start = this.position;
    let digits = 0;
    while (this.position < this.text.length && this.text[this.position] >= "0" && this.text[this.position] <= "9") {
      this.position++; digits++;
    }
    if (this.text[this.position] === ".") {
      this.position++;
      while (this.position < this.text.length && this.text[this.position] >= "0" && this.text[this.position] <= "9") {
        this.position++; digits++;
      }
    }
    if (digits === 0) throw new CalculatorError("expected number");
    if (this.text[this.position] === "e" || this.text[this.position] === "E") {
      this.position++;
      if (this.text[this.position] === "+" || this.text[this.position] === "-") this.position++;
      const exponentStart = this.position;
      while (this.position < this.text.length && this.text[this.position] >= "0" && this.text[this.position] <= "9") this.position++;
      if (this.position === exponentStart) throw new CalculatorError("malformed exponent");
    }
    return this.finite(Number(this.text.slice(start, this.position)));
  }
}

if (process.argv.length !== 3) {
  console.error("error: expected exactly one expression argument");
  process.exit(1);
}

try {
  console.log(new Parser(process.argv[2]).parse());
} catch (error: unknown) {
  console.error(`error: ${error instanceof Error ? error.message : String(error)}`);
  process.exit(1);
}
