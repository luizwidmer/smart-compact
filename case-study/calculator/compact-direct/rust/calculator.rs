use std::{env, process};

struct Parser<'a> { text: &'a [u8], pos: usize }

impl<'a> Parser<'a> {
    fn new(text: &'a str) -> Self { Self { text: text.as_bytes(), pos: 0 } }
    fn skip(&mut self) {
        while self.pos < self.text.len() && (self.text[self.pos] == b' ' || (b'\t'..=b'\r').contains(&self.text[self.pos])) {
            self.pos += 1;
        }
    }
    fn take(&mut self, byte: u8) -> bool { self.skip(); if self.text.get(self.pos) == Some(&byte) { self.pos += 1; true } else { false } }
    fn parse(&mut self) -> Result<f64, String> {
        let value = self.expression()?;
        self.skip();
        if self.pos != self.text.len() { return Err("unexpected token".into()); }
        Ok(value)
    }
    fn expression(&mut self) -> Result<f64, String> {
        let mut value = self.term()?;
        loop {
            if self.take(b'+') { value = checked(value + self.term()?)?; }
            else if self.take(b'-') { value = checked(value - self.term()?)?; }
            else { return Ok(value); }
        }
    }
    fn term(&mut self) -> Result<f64, String> {
        let mut value = self.unary()?;
        loop {
            if self.take(b'*') { value = checked(value * self.unary()?)?; }
            else if self.take(b'/') {
                let rhs = self.unary()?;
                if rhs == 0.0 { return Err("division by zero".into()); }
                value = checked(value / rhs)?;
            } else if self.take(b'%') {
                let rhs = self.unary()?;
                if rhs == 0.0 { return Err("remainder by zero".into()); }
                value = checked(value % rhs)?;
            } else { return Ok(value); }
        }
    }
    fn unary(&mut self) -> Result<f64, String> {
        if self.take(b'+') { return self.unary(); }
        if self.take(b'-') { return checked(-self.unary()?); }
        self.power()
    }
    fn power(&mut self) -> Result<f64, String> {
        let mut value = self.primary()?;
        if self.take(b'^') { value = checked(value.powf(self.unary()?))?; }
        Ok(value)
    }
    fn primary(&mut self) -> Result<f64, String> {
        if self.take(b'(') {
            let value = self.expression()?;
            if !self.take(b')') { return Err("expected ')'".into()); }
            return Ok(value);
        }
        self.number()
    }
    fn number(&mut self) -> Result<f64, String> {
        self.skip();
        let start = self.pos;
        let mut digits = 0;
        while self.text.get(self.pos).is_some_and(u8::is_ascii_digit) { self.pos += 1; digits += 1; }
        if self.text.get(self.pos) == Some(&b'.') {
            self.pos += 1;
            while self.text.get(self.pos).is_some_and(u8::is_ascii_digit) { self.pos += 1; digits += 1; }
        }
        if digits == 0 { return Err("expected number".into()); }
        if matches!(self.text.get(self.pos), Some(b'e' | b'E')) {
            self.pos += 1;
            if matches!(self.text.get(self.pos), Some(b'+' | b'-')) { self.pos += 1; }
            let exponent = self.pos;
            while self.text.get(self.pos).is_some_and(u8::is_ascii_digit) { self.pos += 1; }
            if self.pos == exponent { return Err("malformed exponent".into()); }
        }
        let token = std::str::from_utf8(&self.text[start..self.pos]).map_err(|_| "invalid input")?;
        checked(token.parse::<f64>().map_err(|_| "invalid number")?)
    }
}

fn checked(value: f64) -> Result<f64, String> {
    if value.is_finite() { Ok(value) } else { Err("non-finite value".into()) }
}

fn run() -> Result<(), String> {
    let args: Vec<_> = env::args_os().collect();
    if args.len() != 2 { return Err("expected exactly one expression".into()); }
    let expression = args[1].to_str().ok_or("expression is not valid UTF-8")?;
    println!("{}", Parser::new(expression).parse()?);
    Ok(())
}

fn main() {
    if let Err(error) = run() { eprintln!("error: {error}"); process::exit(1); }
}
