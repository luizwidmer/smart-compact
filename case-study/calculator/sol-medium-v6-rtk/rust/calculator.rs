use std::{env, process};
struct Parser { s: Vec<u8>, p: usize }
fn check(v:f64)->Result<f64,()>{if v.is_finite(){Ok(v)}else{Err(())}}
impl Parser {
 fn space(&mut self){while self.p<self.s.len()&&matches!(self.s[self.p],b' '|b'\t'|b'\n'|b'\r'|0x0b|0x0c){self.p+=1}}
 fn take(&mut self,c:u8)->bool{self.space();if self.p<self.s.len()&&self.s[self.p]==c{self.p+=1;true}else{false}}
 fn expression(&mut self)->Result<f64,()>{let mut v=self.term()?;loop{if self.take(b'+'){v=check(v+self.term()?)?}else if self.take(b'-'){v=check(v-self.term()?)?}else{return Ok(v)}}}
 fn term(&mut self)->Result<f64,()>{let mut v=self.unary()?;loop{if self.take(b'*'){v=check(v*self.unary()?)?}else if self.take(b'/'){let r=self.unary()?;if r==0.0{return Err(())}v=check(v/r)?}else if self.take(b'%'){let r=self.unary()?;if r==0.0{return Err(())}v=check(v%r)?}else{return Ok(v)}}}
 fn unary(&mut self)->Result<f64,()>{if self.take(b'+'){self.unary()}else if self.take(b'-'){let v=self.unary()?;check(-v)}else{self.power()}}
 fn power(&mut self)->Result<f64,()>{let mut v=self.primary()?;if self.take(b'^'){v=check(v.powf(self.unary()?))?}Ok(v)}
 fn primary(&mut self)->Result<f64,()>{if self.take(b'('){let v=self.expression()?;if !self.take(b')'){return Err(())}return Ok(v)}self.space();let start=self.p;while self.p<self.s.len()&&self.s[self.p].is_ascii_digit(){self.p+=1}if self.p<self.s.len()&&self.s[self.p]==b'.'{self.p+=1;while self.p<self.s.len()&&self.s[self.p].is_ascii_digit(){self.p+=1}}if self.p==start||(self.p==start+1&&self.s[start]==b'.'){return Err(())}if self.p<self.s.len()&&matches!(self.s[self.p],b'e'|b'E'){self.p+=1;if self.p<self.s.len()&&matches!(self.s[self.p],b'+'|b'-'){self.p+=1}let es=self.p;while self.p<self.s.len()&&self.s[self.p].is_ascii_digit(){self.p+=1}if self.p==es{return Err(())}}let t=std::str::from_utf8(&self.s[start..self.p]).map_err(|_|())?;check(t.parse().map_err(|_|())?)}
}
fn run()->Result<f64,()>{let a:Vec<String>=env::args().collect();if a.len()!=2{return Err(())}let mut p=Parser{s:a[1].as_bytes().to_vec(),p:0};let v=p.expression()?;p.space();if p.p!=p.s.len(){Err(())}else{Ok(v)}}
fn main(){match run(){Ok(v)=>println!("{:.17}",v),Err(_)=>{eprintln!("error: invalid expression");process::exit(1)}}}
