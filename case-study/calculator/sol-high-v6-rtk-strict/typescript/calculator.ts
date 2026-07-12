const numberPattern: RegExp = /^(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?/;

class Parser {
  private pos: number = 0;
  private text: string;
  constructor(text: string) { this.text = text; }
  private space(): void { while (this.pos < this.text.length && /[\t\n\v\f\r ]/.test(this.text[this.pos])) this.pos++; }
  private take(ch: string): boolean { this.space(); if (this.text.startsWith(ch, this.pos)) { this.pos += ch.length; return true; } return false; }
  private checked(value: number): number { if (!Number.isFinite(value)) throw new Error("non-finite value"); return value; }
  private expression(): number {
    let value = this.product();
    for (;;) {
      if (this.take("+")) value = this.checked(value + this.product());
      else if (this.take("-")) value = this.checked(value - this.product());
      else return value;
    }
  }
  private product(): number {
    let value = this.unary();
    for (;;) {
      if (this.take("*")) value = this.checked(value * this.unary());
      else if (this.take("/")) { const rhs = this.unary(); if (rhs === 0) throw new Error("division by zero"); value = this.checked(value / rhs); }
      else if (this.take("%")) { const rhs = this.unary(); if (rhs === 0) throw new Error("remainder by zero"); value = this.checked(value % rhs); }
      else return value;
    }
  }
  private unary(): number { if (this.take("+")) return this.unary(); if (this.take("-")) return this.checked(-this.unary()); return this.power(); }
  private power(): number { let value = this.primary(); if (this.take("^")) value = this.checked(Math.pow(value, this.unary())); return value; }
  private primary(): number {
    if (this.take("(")) { const value = this.expression(); if (!this.take(")")) throw new Error("expected closing parenthesis"); return value; }
    this.space(); const match = this.text.slice(this.pos).match(numberPattern);
    if (!match) throw new Error("expected number");
    this.pos += match[0].length; return this.checked(Number(match[0]));
  }
  parse(): number { const value = this.expression(); this.space(); if (this.pos !== this.text.length) throw new Error("trailing input"); return value; }
}

try {
  if (process.argv.length !== 3) throw new Error("expected exactly one expression");
  console.log(new Parser(process.argv[2]).parse().toPrecision(17).replace(/(?:\.0+|(?:(\.\d*?)0+))(?=e|$)/, "$1"));
} catch (error: unknown) {
  console.error(`error: ${error instanceof Error ? error.message : "unknown error"}`);
  process.exit(1);
}
