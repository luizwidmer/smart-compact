class CalculatorError extends Error {}

class Parser {
  private position = 0;
  private readonly text: string;

  constructor(text: string) {
    this.text = text;
  }

  private skipSpace(): void {
    while (this.position < this.text.length && " \t\n\r\v\f".includes(this.text[this.position])) this.position++;
  }

  private take(char: string): boolean {
    this.skipSpace();
    if (this.text[this.position] === char) { this.position++; return true; }
    return false;
  }

  parse(): number {
    const value = this.additive();
    this.skipSpace();
    if (this.position !== this.text.length) throw new CalculatorError("unexpected token");
    return value;
  }

  private additive(): number {
    let value = this.multiplicative();
    while (true) {
      if (this.take("+")) value = checked(value + this.multiplicative());
      else if (this.take("-")) value = checked(value - this.multiplicative());
      else return value;
    }
  }

  private multiplicative(): number {
    let value = this.unary();
    while (true) {
      if (this.take("*")) value = checked(value * this.unary());
      else if (this.take("/")) {
        const divisor = this.unary();
        if (divisor === 0) throw new CalculatorError("division by zero");
        value = checked(value / divisor);
      } else if (this.take("%")) {
        const divisor = this.unary();
        if (divisor === 0) throw new CalculatorError("remainder by zero");
        value = checked(value % divisor);
      } else return value;
    }
  }

  private unary(): number {
    if (this.take("+")) return this.unary();
    if (this.take("-")) return checked(-this.unary());
    return this.power();
  }

  private power(): number {
    let value = this.primary();
    if (this.take("^")) value = checked(Math.pow(value, this.unary()));
    return value;
  }

  private primary(): number {
    if (this.take("(")) {
      const value = this.additive();
      if (!this.take(")")) throw new CalculatorError("expected closing parenthesis");
      return value;
    }
    return this.number();
  }

  private number(): number {
    this.skipSpace();
    const start = this.position;
    let before = 0;
    while (isDigit(this.text[this.position])) { this.position++; before++; }
    let after = 0;
    if (this.text[this.position] === ".") {
      this.position++;
      while (isDigit(this.text[this.position])) { this.position++; after++; }
    }
    if (before === 0 && after === 0) throw new CalculatorError("expected number");
    if (this.text[this.position] === "e" || this.text[this.position] === "E") {
      this.position++;
      if (this.text[this.position] === "+" || this.text[this.position] === "-") this.position++;
      const exponentStart = this.position;
      while (isDigit(this.text[this.position])) this.position++;
      if (this.position === exponentStart) throw new CalculatorError("malformed exponent");
    }
    return checked(Number(this.text.slice(start, this.position)));
  }
}

function isDigit(char: string | undefined): boolean {
  return char !== undefined && char >= "0" && char <= "9";
}

function checked(value: number): number {
  if (!Number.isFinite(value)) throw new CalculatorError("non-finite result");
  return value;
}

if (process.argv.length !== 3) {
  console.error("error: expected exactly one expression");
  process.exit(1);
}
try {
  console.log(new Parser(process.argv[2]).parse());
} catch (error: unknown) {
  console.error(`error: ${error instanceof Error ? error.message : String(error)}`);
  process.exit(1);
}
