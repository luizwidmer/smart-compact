use std::{env, process};

struct Parser { input: Vec<u8>, pos: usize }

impl Parser {
    fn new(s: &str) -> Self { Self { input: s.as_bytes().to_vec(), pos: 0 } }
    fn space(&mut self) { while self.pos < self.input.len() && matches!(self.input[self.pos], b' '|b'\t'|b'\n'|b'\r'|0x0c|0x0b) { self.pos += 1; } }
    fn take(&mut self, c: u8) -> bool { self.space(); if self.input.get(self.pos) == Some(&c) { self.pos += 1; true } else { false } }
    fn parse(&mut self) -> Result<f64, String> { let v = self.add()?; self.space(); if self.pos != self.input.len() { Err("unexpected token".into()) } else { Ok(v) } }
    fn add(&mut self) -> Result<f64, String> {
        let mut v = self.mul()?;
        loop { if self.take(b'+') { let r=self.mul()?; v=finite(v+r)?; } else if self.take(b'-') { let r=self.mul()?; v=finite(v-r)?; } else { return Ok(v); } }
    }
    fn mul(&mut self) -> Result<f64, String> {
        let mut v=self.unary()?;
        loop {
            if self.take(b'*') { let r=self.unary()?; v=finite(v*r)?; }
            else if self.take(b'/') { let r=self.unary()?; if r==0.0 { return Err("division by zero".into()); } v=finite(v/r)?; }
            else if self.take(b'%') { let r=self.unary()?; if r==0.0 { return Err("remainder by zero".into()); } v=finite(v%r)?; }
            else { return Ok(v); }
        }
    }
    fn unary(&mut self) -> Result<f64, String> { if self.take(b'+') { self.unary() } else if self.take(b'-') { let v=self.unary()?; finite(-v) } else { self.power() } }
    fn power(&mut self) -> Result<f64, String> { let mut v=self.primary()?; if self.take(b'^') { let r=self.unary()?; v=finite(v.powf(r))?; } Ok(v) }
    fn primary(&mut self) -> Result<f64, String> {
        if self.take(b'(') { let v=self.add()?; if !self.take(b')') { return Err("expected closing parenthesis".into()); } return Ok(v); }
        self.space(); let start=self.pos;
        let mut before=0; while self.pos<self.input.len() && self.input[self.pos].is_ascii_digit() { self.pos+=1; before+=1; }
        let mut after=0; if self.input.get(self.pos)==Some(&b'.') { self.pos+=1; while self.pos<self.input.len() && self.input[self.pos].is_ascii_digit() { self.pos+=1; after+=1; } }
        if before+after==0 { return Err("expected number".into()); }
        if matches!(self.input.get(self.pos), Some(b'e')|Some(b'E')) { self.pos+=1; if matches!(self.input.get(self.pos), Some(b'+')|Some(b'-')) { self.pos+=1; } let es=self.pos; while self.pos<self.input.len() && self.input[self.pos].is_ascii_digit() { self.pos+=1; } if es==self.pos { return Err("malformed exponent".into()); } }
        let s=std::str::from_utf8(&self.input[start..self.pos]).map_err(|_| "invalid input")?;
        finite(s.parse::<f64>().map_err(|_| "invalid number")?)
    }
}

fn finite(v:f64)->Result<f64,String>{ if v.is_finite(){Ok(v)}else{Err("non-finite result".into())} }
fn main(){ let args:Vec<String>=env::args().collect(); let result=if args.len()!=2{Err("expected exactly one expression".into())}else{Parser::new(&args[1]).parse()}; match result{Ok(v)=>println!("{}",v),Err(e)=>{eprintln!("error: {}",e);process::exit(1)}} }
