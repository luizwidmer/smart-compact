'use strict';
const number = /^(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?/;
class Parser {
  constructor(text) { this.text = text; this.pos = 0; }
  space() { while (this.pos < this.text.length && /[\t\n\v\f\r ]/.test(this.text[this.pos])) this.pos++; }
  take(c) { this.space(); if (this.text.startsWith(c, this.pos)) { this.pos += c.length; return true; } return false; }
  expression() { let v = this.term(); for (;;) { if (this.take('+')) v = check(v + this.term()); else if (this.take('-')) v = check(v - this.term()); else return v; } }
  term() { let v = this.unary(); for (;;) { if (this.take('*')) v = check(v * this.unary()); else if (this.take('/')) { const r=this.unary(); if(r===0) fail(); v=check(v/r); } else if(this.take('%')) { const r=this.unary(); if(r===0) fail(); v=check(v%r); } else return v; } }
  unary() { if(this.take('+')) return this.unary(); if(this.take('-')) return check(-this.unary()); return this.power(); }
  power() { let v=this.primary(); if(this.take('^')) v=check(Math.pow(v,this.unary())); return v; }
  primary() { if(this.take('(')) { const v=this.expression(); if(!this.take(')')) fail(); return v; } this.space(); const m=this.text.slice(this.pos).match(number); if(!m) fail(); this.pos+=m[0].length; return check(Number(m[0])); }
}
function fail(){ throw new Error('invalid'); }
function check(v){ if(!Number.isFinite(v)) fail(); return v; }
try { if(process.argv.length!==3) fail(); const p=new Parser(process.argv[2]); const v=p.expression(); p.space(); if(p.pos!==p.text.length) fail(); console.log(v.toString()); }
catch (_) { console.error('error: invalid expression'); process.exit(1); }
