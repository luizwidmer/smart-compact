use std::env;
use std::process;

struct Parser<'a> {
    text: &'a [u8],
    pos: usize,
}

impl<'a> Parser<'a> {
    fn new(text: &'a str) -> Self {
        Self { text: text.as_bytes(), pos: 0 }
    }

    fn skip_space(&mut self) {
        while self.pos < self.text.len() && matches!(self.text[self.pos], b' ' | b'\t' | b'\n' | b'\r' | 0x0b | 0x0c) {
            self.pos += 1;
        }
    }

    fn take(&mut self, wanted: u8) -> bool {
        self.skip_space();
        if self.pos < self.text.len() && self.text[self.pos] == wanted {
            self.pos += 1;
            true
        } else {
            false
        }
    }

    fn parse(&mut self) -> Result<f64, String> {
        let value = self.addition()?;
        self.skip_space();
        if self.pos != self.text.len() { return Err("trailing token".into()); }
        Ok(value)
    }

    fn addition(&mut self) -> Result<f64, String> {
        let mut value = self.multiplication()?;
        loop {
            if self.take(b'+') { value = checked(value + self.multiplication()?)?; }
            else if self.take(b'-') { value = checked(value - self.multiplication()?)?; }
            else { return Ok(value); }
        }
    }

    fn multiplication(&mut self) -> Result<f64, String> {
        let mut value = self.unary()?;
        loop {
            if self.take(b'*') { value = checked(value * self.unary()?)?; }
            else if self.take(b'/') {
                let right = self.unary()?;
                if right == 0.0 { return Err("division by zero".into()); }
                value = checked(value / right)?;
            } else if self.take(b'%') {
                let right = self.unary()?;
                if right == 0.0 { return Err("remainder by zero".into()); }
                value = checked(value % right)?;
            } else { return Ok(value); }
        }
    }

    fn unary(&mut self) -> Result<f64, String> {
        if self.take(b'+') { return self.unary(); }
        if self.take(b'-') { return checked(-self.unary()?) ; }
        self.power()
    }

    fn power(&mut self) -> Result<f64, String> {
        let value = self.primary()?;
        if self.take(b'^') { return checked(value.powf(self.unary()?)); }
        Ok(value)
    }

    fn primary(&mut self) -> Result<f64, String> {
        if self.take(b'(') {
            let value = self.addition()?;
            if !self.take(b')') { return Err("missing closing parenthesis".into()); }
            return Ok(value);
        }
        self.skip_space();
        let start = self.pos;
        let mut digits_before = 0;
        while self.pos < self.text.len() && self.text[self.pos].is_ascii_digit() {
            self.pos += 1;
            digits_before += 1;
        }
        if self.pos < self.text.len() && self.text[self.pos] == b'.' {
            self.pos += 1;
            while self.pos < self.text.len() && self.text[self.pos].is_ascii_digit() { self.pos += 1; }
        } else if digits_before == 0 {
            return Err("expected number or parenthesis".into());
        }
        if digits_before == 0 && self.pos == start + 1 { return Err("expected digits".into()); }
        if self.pos < self.text.len() && matches!(self.text[self.pos], b'e' | b'E') {
            self.pos += 1;
            if self.pos < self.text.len() && matches!(self.text[self.pos], b'+' | b'-') { self.pos += 1; }
            let exponent_start = self.pos;
            while self.pos < self.text.len() && self.text[self.pos].is_ascii_digit() { self.pos += 1; }
            if exponent_start == self.pos { return Err("invalid exponent".into()); }
        }
        let token = std::str::from_utf8(&self.text[start..self.pos]).unwrap();
        checked(token.parse::<f64>().map_err(|_| "invalid number".to_string())?)
    }
}

fn checked(value: f64) -> Result<f64, String> {
    if value.is_finite() { Ok(value) } else { Err("non-finite result".into()) }
}

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() != 2 {
        eprintln!("error: expected exactly one expression");
        process::exit(2);
    }
    match Parser::new(&args[1]).parse() {
        Ok(value) => println!("{:.17e}", value),
        Err(message) => { eprintln!("error: {}", message); process::exit(1); }
    }
}
