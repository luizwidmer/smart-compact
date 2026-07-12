'use strict';
class Parser {
  constructor(s) { this.s=s; this.p=0; }
  space(){while(this.p<this.s.length&&' \t\n\r\f\v'.includes(this.s[this.p]))this.p++;}
  take(c){this.space();if(this.s[this.p]===c){this.p++;return true;}return false;}
  parse(){const v=this.add();this.space();if(this.p!==this.s.length)throw Error('unexpected token');return v;}
  add(){let v=this.mul();for(;;){if(this.take('+'))v=ok(v+this.mul());else if(this.take('-'))v=ok(v-this.mul());else return v;}}
  mul(){let v=this.unary();for(;;){if(this.take('*'))v=ok(v*this.unary());else if(this.take('/')){const r=this.unary();if(r===0)throw Error('division by zero');v=ok(v/r);}else if(this.take('%')){const r=this.unary();if(r===0)throw Error('remainder by zero');v=ok(v%r);}else return v;}}
  unary(){if(this.take('+'))return this.unary();if(this.take('-'))return ok(-this.unary());return this.power();}
  power(){let v=this.primary();if(this.take('^'))v=ok(Math.pow(v,this.unary()));return v;}
  primary(){if(this.take('(')){const v=this.add();if(!this.take(')'))throw Error('expected closing parenthesis');return v;}this.space();const m=/^(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?/.exec(this.s.slice(this.p));if(!m)throw Error('expected number');this.p+=m[0].length;return ok(Number(m[0]));}
}
function ok(v){if(!Number.isFinite(v))throw Error('non-finite result');return v;}
try{if(process.argv.length!==3)throw Error('expected exactly one expression');console.log(String(new Parser(process.argv[2]).parse()));}catch(e){console.error('error: '+e.message);process.exit(1);}
