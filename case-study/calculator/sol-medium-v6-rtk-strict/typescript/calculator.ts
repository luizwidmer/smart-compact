class Parser {
  s: string; i: number;
  constructor(s: string) { this.s=s; this.i=0; }
  ws(): void { while(this.i<this.s.length && /[\t\n\v\f\r ]/.test(this.s[this.i])) this.i++; }
  eat(c: string): boolean { this.ws(); if(this.s.startsWith(c,this.i)){this.i+=c.length;return true} return false; }
  num(): number { this.ws(); const m=this.s.slice(this.i).match(/^(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?/); if(!m) throw Error('expected number');this.i+=m[0].length;return this.ck(Number(m[0])); }
  primary(): number {if(this.eat('(')){const v=this.add();if(!this.eat(')'))throw Error("expected ')'");return v}return this.num()}
  power(): number {let v=this.primary();if(this.eat('^'))v=Math.pow(v,this.unary());return this.ck(v)}
  unary(): number {if(this.eat('+'))return this.ck(this.unary());if(this.eat('-'))return this.ck(-this.unary());return this.power()}
  mul(): number {let v=this.unary();for(;;){if(this.eat('*'))v*=this.unary();else if(this.eat('/')){const r=this.unary();if(r===0)throw Error('division by zero');v/=r}else if(this.eat('%')){const r=this.unary();if(r===0)throw Error('remainder by zero');v%=r}else return v;v=this.ck(v)}}
  add(): number {let v=this.mul();for(;;){if(this.eat('+'))v+=this.mul();else if(this.eat('-'))v-=this.mul();else return v;v=this.ck(v)}}
  ck(v: number): number {if(!Number.isFinite(v))throw Error('non-finite value');return v}
  parse(): number {const v=this.add();this.ws();if(this.i!==this.s.length)throw Error('trailing token');return v}
}
try{if(process.argv.length!==3)throw Error('expected one expression');console.log(new Parser(process.argv[2]).parse().toString())}catch(e){console.error('error: '+(e as Error).message);process.exit(1)}
