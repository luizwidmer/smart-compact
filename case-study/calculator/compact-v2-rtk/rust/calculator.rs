use std::env;
use std::process;

struct Parser {
    input: Vec<u8>,
    pos: usize,
}

impl Parser {
    fn new(text: &str) -> Self { Self { input: text.as_bytes().to_vec(), pos: 0 } }

    fn skip_space(&mut self) {
        while self.pos < self.input.len() && matches!(self.input[self.pos], b' ' | b'\t' | b'\n' | b'\r' | 0x0b | 0x0c) {
            self.pos += 1;
        }
    }

    fn take(&mut self, token: u8) -> bool {
        self.skip_space();
        if self.input.get(self.pos) == Some(&token) { self.pos += 1; true } else { false }
    }

    fn parse(&mut self) -> Result<f64, String> {
        let value = self.expression()?;
        self.skip_space();
        if self.pos != self.input.len() { return Err("unexpected token".into()); }
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
            if !self.take(b')') { return Err("missing closing parenthesis".into()); }
            return Ok(value);
        }
        self.number()
    }

    fn number(&mut self) -> Result<f64, String> {
        self.skip_space();
        let start = self.pos;
        let mut digits = 0;
        while self.input.get(self.pos).is_some_and(u8::is_ascii_digit) { self.pos += 1; digits += 1; }
        if self.input.get(self.pos) == Some(&b'.') {
            self.pos += 1;
            while self.input.get(self.pos).is_some_and(u8::is_ascii_digit) { self.pos += 1; digits += 1; }
        }
        if digits == 0 { return Err("expected number".into()); }
        if matches!(self.input.get(self.pos), Some(b'e' | b'E')) {
            self.pos += 1;
            if matches!(self.input.get(self.pos), Some(b'+' | b'-')) { self.pos += 1; }
            let exponent = self.pos;
            while self.input.get(self.pos).is_some_and(u8::is_ascii_digit) { self.pos += 1; }
            if self.pos == exponent { return Err("malformed exponent".into()); }
        }
        let token = std::str::from_utf8(&self.input[start..self.pos]).map_err(|_| "invalid number")?;
        checked(token.parse::<f64>().map_err(|_| "invalid number")?)
    }
}

fn checked(value: f64) -> Result<f64, String> {
    if value.is_finite() { Ok(value) } else { Err("non-finite result".into()) }
}

fn run() -> Result<(), String> {
    let args: Vec<String> = env::args().collect();
    if args.len() != 2 { return Err("expected exactly one expression".into()); }
    println!("{}", Parser::new(&args[1]).parse()?);
    Ok(())
}

fn main() {
    if let Err(error) = run() { eprintln!("error: {}", error); process::exit(1); }
}
