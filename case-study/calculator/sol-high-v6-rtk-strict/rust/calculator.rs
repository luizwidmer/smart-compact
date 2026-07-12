use std::{env, process};

struct Parser { input: Vec<u8>, pos: usize }

impl Parser {
    fn new(text: String) -> Self { Self { input: text.into_bytes(), pos: 0 } }
    fn space(&mut self) { while self.pos < self.input.len() && matches!(self.input[self.pos], b' ' | b'\t' | b'\n' | b'\r' | 0x0b | 0x0c) { self.pos += 1; } }
    fn take(&mut self, ch: u8) -> bool { self.space(); if self.input.get(self.pos) == Some(&ch) { self.pos += 1; true } else { false } }
    fn checked(value: f64) -> Result<f64, String> { if value.is_finite() { Ok(value) } else { Err("non-finite value".into()) } }
    fn expression(&mut self) -> Result<f64, String> {
        let mut value = self.product()?;
        loop { if self.take(b'+') { value = Self::checked(value + self.product()?)?; } else if self.take(b'-') { value = Self::checked(value - self.product()?)?; } else { return Ok(value); } }
    }
    fn product(&mut self) -> Result<f64, String> {
        let mut value = self.unary()?;
        loop {
            if self.take(b'*') { value = Self::checked(value * self.unary()?)?; }
            else if self.take(b'/') { let rhs = self.unary()?; if rhs == 0.0 { return Err("division by zero".into()); } value = Self::checked(value / rhs)?; }
            else if self.take(b'%') { let rhs = self.unary()?; if rhs == 0.0 { return Err("remainder by zero".into()); } value = Self::checked(value % rhs)?; }
            else { return Ok(value); }
        }
    }
    fn unary(&mut self) -> Result<f64, String> { if self.take(b'+') { self.unary() } else if self.take(b'-') { let value = self.unary()?; Self::checked(-value) } else { self.power() } }
    fn power(&mut self) -> Result<f64, String> { let mut value = self.primary()?; if self.take(b'^') { value = Self::checked(value.powf(self.unary()?))?; } Ok(value) }
    fn primary(&mut self) -> Result<f64, String> {
        if self.take(b'(') { let value = self.expression()?; if !self.take(b')') { return Err("expected closing parenthesis".into()); } return Ok(value); }
        self.space(); let start = self.pos; let mut digits = false;
        while self.input.get(self.pos).is_some_and(u8::is_ascii_digit) { self.pos += 1; digits = true; }
        if self.input.get(self.pos) == Some(&b'.') { self.pos += 1; while self.input.get(self.pos).is_some_and(u8::is_ascii_digit) { self.pos += 1; digits = true; } }
        if !digits { return Err("expected number".into()); }
        if matches!(self.input.get(self.pos), Some(b'e' | b'E')) { self.pos += 1; if matches!(self.input.get(self.pos), Some(b'+' | b'-')) { self.pos += 1; } let exp = self.pos; while self.input.get(self.pos).is_some_and(u8::is_ascii_digit) { self.pos += 1; } if self.pos == exp { return Err("malformed exponent".into()); } }
        let text = std::str::from_utf8(&self.input[start..self.pos]).map_err(|_| "invalid input")?;
        Self::checked(text.parse::<f64>().map_err(|_| "invalid number")?)
    }
    fn parse(&mut self) -> Result<f64, String> { let value = self.expression()?; self.space(); if self.pos != self.input.len() { Err("trailing input".into()) } else { Ok(value) } }
}

fn run() -> Result<(), String> {
    let mut args = env::args(); args.next(); let expression = args.next().ok_or("expected exactly one expression")?; if args.next().is_some() { return Err("expected exactly one expression".into()); }
    println!("{}", Parser::new(expression).parse()?); Ok(())
}
fn main() { if let Err(error) = run() { eprintln!("error: {}", error); process::exit(1); } }
