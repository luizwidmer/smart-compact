use std::env;
use std::process;

struct Parser<'a> {
    input: &'a [u8],
    pos: usize,
}

impl<'a> Parser<'a> {
    fn new(input: &'a str) -> Self {
        Self { input: input.as_bytes(), pos: 0 }
    }

    fn skip_whitespace(&mut self) {
        while self.pos < self.input.len()
            && matches!(self.input[self.pos], b' ' | b'\t' | b'\n' | b'\r' | 0x0c | 0x0b)
        {
            self.pos += 1;
        }
    }

    fn consume(&mut self, token: u8) -> bool {
        self.skip_whitespace();
        if self.input.get(self.pos) == Some(&token) {
            self.pos += 1;
            true
        } else {
            false
        }
    }

    fn checked(value: f64) -> Result<f64, String> {
        if value.is_finite() { Ok(value) } else { Err("non-finite result".into()) }
    }

    fn parse(&mut self) -> Result<f64, String> {
        let value = self.expression()?;
        self.skip_whitespace();
        if self.pos != self.input.len() {
            return Err("unexpected trailing input".into());
        }
        Ok(value)
    }

    fn expression(&mut self) -> Result<f64, String> {
        let mut value = self.term()?;
        loop {
            if self.consume(b'+') {
                value = Self::checked(value + self.term()?)?;
            } else if self.consume(b'-') {
                value = Self::checked(value - self.term()?)?;
            } else {
                return Ok(value);
            }
        }
    }

    fn term(&mut self) -> Result<f64, String> {
        let mut value = self.unary()?;
        loop {
            if self.consume(b'*') {
                value = Self::checked(value * self.unary()?)?;
            } else if self.consume(b'/') {
                let divisor = self.unary()?;
                if divisor == 0.0 { return Err("division by zero".into()); }
                value = Self::checked(value / divisor)?;
            } else if self.consume(b'%') {
                let divisor = self.unary()?;
                if divisor == 0.0 { return Err("remainder by zero".into()); }
                value = Self::checked(value % divisor)?;
            } else {
                return Ok(value);
            }
        }
    }

    fn unary(&mut self) -> Result<f64, String> {
        if self.consume(b'+') {
            return Self::checked(self.unary()?);
        }
        if self.consume(b'-') {
            let value = self.unary()?;
            return Self::checked(-value);
        }
        self.power()
    }

    fn power(&mut self) -> Result<f64, String> {
        let base = self.primary()?;
        if self.consume(b'^') {
            let exponent = self.unary()?;
            Self::checked(base.powf(exponent))
        } else {
            Ok(base)
        }
    }

    fn primary(&mut self) -> Result<f64, String> {
        if self.consume(b'(') {
            let value = self.expression()?;
            if !self.consume(b')') { return Err("expected ')'".into()); }
            return Ok(value);
        }
        self.number()
    }

    fn number(&mut self) -> Result<f64, String> {
        self.skip_whitespace();
        let start = self.pos;
        let mut digits = 0usize;
        while self.input.get(self.pos).is_some_and(u8::is_ascii_digit) {
            self.pos += 1;
            digits += 1;
        }
        if self.input.get(self.pos) == Some(&b'.') {
            self.pos += 1;
            while self.input.get(self.pos).is_some_and(u8::is_ascii_digit) {
                self.pos += 1;
                digits += 1;
            }
        }
        if digits == 0 { return Err("expected number".into()); }
        if matches!(self.input.get(self.pos), Some(b'e' | b'E')) {
            self.pos += 1;
            if matches!(self.input.get(self.pos), Some(b'+' | b'-')) { self.pos += 1; }
            let exponent_start = self.pos;
            while self.input.get(self.pos).is_some_and(u8::is_ascii_digit) { self.pos += 1; }
            if self.pos == exponent_start { return Err("malformed exponent".into()); }
        }
        let token = std::str::from_utf8(&self.input[start..self.pos]).map_err(|_| "invalid number")?;
        let value = token.parse::<f64>().map_err(|_| "invalid number")?;
        Self::checked(value)
    }
}

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() != 2 {
        eprintln!("error: expected exactly one expression argument");
        process::exit(1);
    }
    match Parser::new(&args[1]).parse() {
        Ok(value) => println!("{}", value),
        Err(message) => {
            eprintln!("error: {}", message);
            process::exit(1);
        }
    }
}
