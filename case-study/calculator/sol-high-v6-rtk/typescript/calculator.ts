class CalculatorParser {
  s: string; p: number;
  constructor(s: string) { this.s=s; this.p=0; }
  space(): void {while(this.p<this.s.length&&' \t\n\r\f\v'.includes(this.s[this.p]))this.p++;}
  take(c: string): boolean {this.space();if(this.s[this.p]===c){this.p++;return true;}return false;}
  parse(): number {const v=this.add();this.space();if(this.p!==this.s.length)throw Error('unexpected token');return v;}
  add(): number {let v=this.mul();for(;;){if(this.take('+'))v=valid(v+this.mul());else if(this.take('-'))v=valid(v-this.mul());else return v;}}
  mul(): number {let v=this.unary();for(;;){if(this.take('*'))v=valid(v*this.unary());else if(this.take('/')){const r=this.unary();if(r===0)throw Error('division by zero');v=valid(v/r);}else if(this.take('%')){const r=this.unary();if(r===0)throw Error('remainder by zero');v=valid(v%r);}else return v;}}
  unary(): number {if(this.take('+'))return this.unary();if(this.take('-'))return valid(-this.unary());return this.power();}
  power(): number {let v=this.primary();if(this.take('^'))v=valid(Math.pow(v,this.unary()));return v;}
  primary(): number {if(this.take('(')){const v=this.add();if(!this.take(')'))throw Error('expected closing parenthesis');return v;}this.space();const m=/^(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?/.exec(this.s.slice(this.p));if(!m)throw Error('expected number');this.p+=m[0].length;return valid(Number(m[0]));}
}
function valid(v: number): number {if(!Number.isFinite(v))throw Error('non-finite result');return v;}
try {if(process.argv.length!==3)throw Error('expected exactly one expression');console.log(String(new CalculatorParser(process.argv[2]).parse()));} catch(e) {const message=e instanceof Error?e.message:'calculation failed';console.error('error: '+message);process.exit(1);}
