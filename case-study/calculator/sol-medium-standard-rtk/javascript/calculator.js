"use strict";
const numberPattern = /^(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?/;
function checked(v) { if (!Number.isFinite(v)) throw new Error("non-finite value or result"); return v; }
class Parser {
  constructor(s) { this.s=s; this.p=0; }
  skip(){while(this.p<this.s.length && /[\t\n\v\f\r ]/.test(this.s[this.p]))this.p++;}
  take(c){this.skip();if(this.s[this.p]===c){this.p++;return true;}return false;}
  parse(){const v=this.additive();this.skip();if(this.p!==this.s.length)throw new Error("unexpected token");return checked(v);}
  additive(){let v=this.multiplicative();for(;;){if(this.take('+'))v=checked(v+this.multiplicative());else if(this.take('-'))v=checked(v-this.multiplicative());else return v;}}
  multiplicative(){let v=this.unary();for(;;){if(this.take('*'))v=checked(v*this.unary());else if(this.take('/')){const r=this.unary();if(r===0)throw new Error("division by zero");v=checked(v/r);}else if(this.take('%')){const r=this.unary();if(r===0)throw new Error("remainder by zero");v=checked(v%r);}else return v;}}
  unary(){if(this.take('+'))return this.unary();if(this.take('-'))return checked(-this.unary());return this.power();}
  power(){let v=this.primary();if(this.take('^'))v=checked(Math.pow(v,this.unary()));return v;}
  primary(){if(this.take('(')){const v=this.additive();if(!this.take(')'))throw new Error("expected closing parenthesis");return v;}this.skip();const m=this.s.slice(this.p).match(numberPattern);if(!m)throw new Error("expected number");this.p+=m[0].length;return checked(Number(m[0]));}
}
try{if(process.argv.length!==3)throw new Error("expected exactly one expression");console.log(new Parser(process.argv[2]).parse().toString());}catch(e){console.error(`error: ${e.message}`);process.exit(1);}
