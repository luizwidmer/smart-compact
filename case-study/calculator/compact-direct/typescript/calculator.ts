class Parser {
  private pos = 0;
  private text: string;
  constructor(text: string) { this.text = text; }
  private skip(): void { while (this.pos < this.text.length && " \t\n\r\v\f".includes(this.text[this.pos])) this.pos++; }
  private take(c: string): boolean { this.skip(); if (this.text[this.pos] === c) { this.pos++; return true; } return false; }
  parse(): number { const v = this.expression(); this.skip(); if (this.pos !== this.text.length) throw Error("unexpected token"); return v; }
  private expression(): number {
    let v = this.term();
    for (;;) { if (this.take("+")) v = checked(v + this.term()); else if (this.take("-")) v = checked(v - this.term()); else return v; }
  }
  private term(): number {
    let v = this.unary();
    for (;;) {
      if (this.take("*")) v = checked(v * this.unary());
      else if (this.take("/")) { const r = this.unary(); if (r === 0) throw Error("division by zero"); v = checked(v / r); }
      else if (this.take("%")) { const r = this.unary(); if (r === 0) throw Error("remainder by zero"); v = checked(v % r); }
      else return v;
    }
  }
  private unary(): number { if (this.take("+")) return this.unary(); if (this.take("-")) return checked(-this.unary()); return this.power(); }
  private power(): number { let v = this.primary(); if (this.take("^")) v = checked(Math.pow(v, this.unary())); return v; }
  private primary(): number { if (this.take("(")) { const v = this.expression(); if (!this.take(")")) throw Error("expected ')'"); return v; } return this.number(); }
  private number(): number {
    this.skip(); const start = this.pos; let digits = 0;
    while (isDigit(this.text[this.pos])) { this.pos++; digits++; }
    if (this.text[this.pos] === ".") { this.pos++; while (isDigit(this.text[this.pos])) { this.pos++; digits++; } }
    if (!digits) throw Error("expected number");
    if (this.text[this.pos] === "e" || this.text[this.pos] === "E") {
      this.pos++; if (this.text[this.pos] === "+" || this.text[this.pos] === "-") this.pos++;
      const exponent = this.pos; while (isDigit(this.text[this.pos])) this.pos++;
      if (this.pos === exponent) throw Error("malformed exponent");
    }
    return checked(Number(this.text.slice(start, this.pos)));
  }
}
function isDigit(c: string | undefined): boolean { return c !== undefined && c >= "0" && c <= "9"; }
function checked(v: number): number { if (!Number.isFinite(v)) throw Error("non-finite value"); return v; }
try {
  if (process.argv.length !== 3) throw Error("expected exactly one expression");
  const value = new Parser(process.argv[2]).parse();
  console.log(Object.is(value, -0) ? "-0" : String(value));
} catch (error) {
  console.error(`error: ${(error as Error).message}`);
  process.exit(1);
}
