const numberPattern = /^(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?/;

class Parser {
  constructor(text) { this.text = text; this.pos = 0; }
  space() { while (this.pos < this.text.length && /[\t\n\v\f\r ]/.test(this.text[this.pos])) this.pos++; }
  take(ch) { this.space(); if (this.text.startsWith(ch, this.pos)) { this.pos += ch.length; return true; } return false; }
  checked(value) { if (!Number.isFinite(value)) throw new Error("non-finite value"); return value; }
  expression() {
    let value = this.product();
    for (;;) {
      if (this.take("+")) value = this.checked(value + this.product());
      else if (this.take("-")) value = this.checked(value - this.product());
      else return value;
    }
  }
  product() {
    let value = this.unary();
    for (;;) {
      if (this.take("*")) value = this.checked(value * this.unary());
      else if (this.take("/")) { const rhs = this.unary(); if (rhs === 0) throw new Error("division by zero"); value = this.checked(value / rhs); }
      else if (this.take("%")) { const rhs = this.unary(); if (rhs === 0) throw new Error("remainder by zero"); value = this.checked(value % rhs); }
      else return value;
    }
  }
  unary() { if (this.take("+")) return this.unary(); if (this.take("-")) return this.checked(-this.unary()); return this.power(); }
  power() { let value = this.primary(); if (this.take("^")) value = this.checked(Math.pow(value, this.unary())); return value; }
  primary() {
    if (this.take("(")) { const value = this.expression(); if (!this.take(")")) throw new Error("expected closing parenthesis"); return value; }
    this.space(); const match = this.text.slice(this.pos).match(numberPattern);
    if (!match) throw new Error("expected number");
    this.pos += match[0].length; return this.checked(Number(match[0]));
  }
  parse() { const value = this.expression(); this.space(); if (this.pos !== this.text.length) throw new Error("trailing input"); return value; }
}

try {
  if (process.argv.length !== 3) throw new Error("expected exactly one expression");
  console.log(new Parser(process.argv[2]).parse().toPrecision(17).replace(/(?:\.0+|(?:(\.\d*?)0+))(?=e|$)/, "$1"));
} catch (error) {
  console.error(`error: ${error.message}`);
  process.exit(1);
}
