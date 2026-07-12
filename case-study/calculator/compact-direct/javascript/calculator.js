"use strict";

class Parser {
  constructor(text) { this.text = text; this.pos = 0; }
  skip() { while (this.pos < this.text.length && " \t\n\r\v\f".includes(this.text[this.pos])) this.pos++; }
  take(c) { this.skip(); if (this.text[this.pos] === c) { this.pos++; return true; } return false; }
  parse() { const v = this.expression(); this.skip(); if (this.pos !== this.text.length) throw Error("unexpected token"); return v; }
  expression() {
    let v = this.term();
    for (;;) {
      if (this.take("+")) v = checked(v + this.term());
      else if (this.take("-")) v = checked(v - this.term());
      else return v;
    }
  }
  term() {
    let v = this.unary();
    for (;;) {
      if (this.take("*")) v = checked(v * this.unary());
      else if (this.take("/")) { const r = this.unary(); if (r === 0) throw Error("division by zero"); v = checked(v / r); }
      else if (this.take("%")) { const r = this.unary(); if (r === 0) throw Error("remainder by zero"); v = checked(v % r); }
      else return v;
    }
  }
  unary() { if (this.take("+")) return this.unary(); if (this.take("-")) return checked(-this.unary()); return this.power(); }
  power() { let v = this.primary(); if (this.take("^")) v = checked(Math.pow(v, this.unary())); return v; }
  primary() { if (this.take("(")) { const v = this.expression(); if (!this.take(")")) throw Error("expected ')'"); return v; } return this.number(); }
  number() {
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
const isDigit = c => c >= "0" && c <= "9";
const checked = v => { if (!Number.isFinite(v)) throw Error("non-finite value"); return v; };
try {
  if (process.argv.length !== 3) throw Error("expected exactly one expression");
  const value = new Parser(process.argv[2]).parse();
  console.log(Object.is(value, -0) ? "-0" : String(value));
} catch (error) {
  console.error(`error: ${error.message}`);
  process.exit(1);
}
