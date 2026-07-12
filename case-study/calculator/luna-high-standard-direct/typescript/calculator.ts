"use strict";

class CalculatorError extends Error {}

class Parser {
  private text: string;
  private position: number = 0;

  constructor(text: string) {
    this.text = text;
  }

  private skipSpace(): void {
    while (this.position < this.text.length && " \t\n\r\v\f".includes(this.text[this.position])) {
      this.position += 1;
    }
  }

  private consume(token: string): boolean {
    this.skipSpace();
    if (this.position < this.text.length && this.text[this.position] === token) {
      this.position += 1;
      return true;
    }
    return false;
  }

  private finite(value: number): number {
    if (!Number.isFinite(value)) {
      throw new CalculatorError("non-finite input or result");
    }
    return value;
  }

  parse(): number {
    const value = this.parseAdditive();
    this.skipSpace();
    if (this.position !== this.text.length) {
      throw new CalculatorError("unexpected trailing input");
    }
    return value;
  }

  private parseAdditive(): number {
    let value = this.parseMultiplicative();
    while (true) {
      if (this.consume("+")) {
        value = this.finite(value + this.parseMultiplicative());
      } else if (this.consume("-")) {
        value = this.finite(value - this.parseMultiplicative());
      } else {
        return value;
      }
    }
  }

  private parseMultiplicative(): number {
    let value = this.parseUnary();
    while (true) {
      if (this.consume("*")) {
        value = this.finite(value * this.parseUnary());
      } else if (this.consume("/")) {
        const divisor = this.parseUnary();
        if (divisor === 0) {
          throw new CalculatorError("division by zero");
        }
        value = this.finite(value / divisor);
      } else if (this.consume("%")) {
        const divisor = this.parseUnary();
        if (divisor === 0) {
          throw new CalculatorError("remainder by zero");
        }
        value = this.finite(value % divisor);
      } else {
        return value;
      }
    }
  }

  private parseUnary(): number {
    if (this.consume("+")) {
      return this.parseUnary();
    }
    if (this.consume("-")) {
      return this.finite(-this.parseUnary());
    }
    return this.parsePower();
  }

  private parsePower(): number {
    const value = this.parsePrimary();
    if (this.consume("^")) {
      return this.finite(Math.pow(value, this.parseUnary()));
    }
    return value;
  }

  private parsePrimary(): number {
    if (this.consume("(")) {
      const value = this.parseAdditive();
      if (!this.consume(")")) {
        throw new CalculatorError("expected closing parenthesis");
      }
      return value;
    }
    return this.parseNumber();
  }

  private parseNumber(): number {
    this.skipSpace();
    const start = this.position;
    let digits = 0;
    while (this.position < this.text.length && this.text[this.position] >= "0" && this.text[this.position] <= "9") {
      this.position += 1;
      digits += 1;
    }
    if (this.position < this.text.length && this.text[this.position] === ".") {
      this.position += 1;
      while (this.position < this.text.length && this.text[this.position] >= "0" && this.text[this.position] <= "9") {
        this.position += 1;
        digits += 1;
      }
    }
    if (digits === 0) {
      throw new CalculatorError("expected number");
    }
    if (this.position < this.text.length && (this.text[this.position] === "e" || this.text[this.position] === "E")) {
      this.position += 1;
      if (this.position < this.text.length && (this.text[this.position] === "+" || this.text[this.position] === "-")) {
        this.position += 1;
      }
      const exponentStart = this.position;
      while (this.position < this.text.length && this.text[this.position] >= "0" && this.text[this.position] <= "9") {
        this.position += 1;
      }
      if (this.position === exponentStart) {
        throw new CalculatorError("malformed exponent");
      }
    }
    return this.finite(Number(this.text.slice(start, this.position)));
  }
}

function main(): number {
  const args: string[] = process.argv.slice(2);
  if (args.length !== 1) {
    throw new CalculatorError("expected exactly one expression argument");
  }
  return new Parser(args[0]).parse();
}

try {
  console.log(main());
} catch (error) {
  const message = error instanceof CalculatorError ? error.message : "invalid expression";
  console.error(`error: ${message}`);
  process.exitCode = 1;
}
