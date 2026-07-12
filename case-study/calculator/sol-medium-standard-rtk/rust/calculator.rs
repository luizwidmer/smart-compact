use std::{env, process};

struct Parser { input: Vec<u8>, pos: usize }
impl Parser {
    fn new(s: &str) -> Self { Self { input: s.as_bytes().to_vec(), pos: 0 } }
    fn skip(&mut self) { while self.pos < self.input.len() && self.input[self.pos].is_ascii_whitespace() { self.pos += 1; } }
    fn take(&mut self, c: u8) -> bool { self.skip(); if self.input.get(self.pos) == Some(&c) { self.pos += 1; true } else { false } }
    fn parse(&mut self) -> Result<f64, String> { let v = self.additive()?; self.skip(); if self.pos != self.input.len() { Err("unexpected token".into()) } else { check(v) } }
    fn additive(&mut self) -> Result<f64, String> { let mut v = self.multiplicative()?; loop { if self.take(b'+') { v = check(v + self.multiplicative()?)?; } else if self.take(b'-') { v = check(v - self.multiplicative()?)?; } else { return Ok(v); } } }
    fn multiplicative(&mut self) -> Result<f64, String> { let mut v = self.unary()?; loop { if self.take(b'*') { v = check(v * self.unary()?)?; } else if self.take(b'/') { let r = self.unary()?; if r == 0.0 { return Err("division by zero".into()); } v = check(v / r)?; } else if self.take(b'%') { let r = self.unary()?; if r == 0.0 { return Err("remainder by zero".into()); } v = check(v % r)?; } else { return Ok(v); } } }
    fn unary(&mut self) -> Result<f64, String> { if self.take(b'+') { self.unary() } else if self.take(b'-') { let v = self.unary()?; check(-v) } else { self.power() } }
    fn power(&mut self) -> Result<f64, String> { let mut v = self.primary()?; if self.take(b'^') { v = check(v.powf(self.unary()?))?; } Ok(v) }
    fn primary(&mut self) -> Result<f64, String> {
        if self.take(b'(') { let v = self.additive()?; if !self.take(b')') { return Err("expected closing parenthesis".into()); } return Ok(v); }
        self.skip(); let start = self.pos; let mut digits = false;
        while self.input.get(self.pos).is_some_and(u8::is_ascii_digit) { self.pos += 1; digits = true; }
        if self.input.get(self.pos) == Some(&b'.') { self.pos += 1; while self.input.get(self.pos).is_some_and(u8::is_ascii_digit) { self.pos += 1; digits = true; } }
        if !digits { return Err("expected number".into()); }
        if matches!(self.input.get(self.pos), Some(b'e' | b'E')) { self.pos += 1; if matches!(self.input.get(self.pos), Some(b'+' | b'-')) { self.pos += 1; } let e = self.pos; while self.input.get(self.pos).is_some_and(u8::is_ascii_digit) { self.pos += 1; } if e == self.pos { return Err("malformed exponent".into()); } }
        let s = std::str::from_utf8(&self.input[start..self.pos]).map_err(|_| "invalid input")?;
        check(s.parse::<f64>().map_err(|_| "invalid number")?)
    }
}
fn check(v: f64) -> Result<f64, String> { if v.is_finite() { Ok(v) } else { Err("non-finite value or result".into()) } }
fn run() -> Result<(), String> { let args: Vec<String> = env::args().collect(); if args.len() != 2 { return Err("expected exactly one expression".into()); } let v = Parser::new(&args[1]).parse()?; println!("{}", v); Ok(()) }
fn main() { if let Err(e) = run() { eprintln!("error: {}", e); process::exit(1); } }
