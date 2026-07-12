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

    fn skip_space(&mut self) {
        while self.pos < self.input.len()
            && matches!(self.input[self.pos], b' ' | b'\t' | b'\n' | b'\r' | 0x0c | 0x0b)
        {
            self.pos += 1;
        }
    }

    fn take(&mut self, token: u8) -> bool {
        self.skip_space();
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
        let value = self.additive()?;
        self.skip_space();
        if self.pos != self.input.len() {
            return Err("unexpected trailing input".into());
        }
        Ok(value)
    }

    fn additive(&mut self) -> Result<f64, String> {
        let mut value = self.multiplicative()?;
        loop {
            if self.take(b'+') {
                value = Self::checked(value + self.multiplicative()?)?;
            } else if self.take(b'-') {
                value = Self::checked(value - self.multiplicative()?)?;
            } else {
                return Ok(value);
            }
        }
    }

    fn multiplicative(&mut self) -> Result<f64, String> {
        let mut value = self.unary()?;
        loop {
            if self.take(b'*') {
                value = Self::checked(value * self.unary()?)?;
            } else if self.take(b'/') {
                let divisor = self.unary()?;
                if divisor == 0.0 { return Err("division by zero".into()); }
                value = Self::checked(value / divisor)?;
            } else if self.take(b'%') {
                let divisor = self.unary()?;
                if divisor == 0.0 { return Err("remainder by zero".into()); }
                value = Self::checked(value % divisor)?;
            } else {
                return Ok(value);
            }
        }
    }

    fn unary(&mut self) -> Result<f64, String> {
        if self.take(b'+') {
            self.unary()
        } else if self.take(b'-') {
            Self::checked(-self.unary()?)
        } else {
            self.power()
        }
    }

    fn power(&mut self) -> Result<f64, String> {
        let base = self.primary()?;
        if self.take(b'^') {
            Self::checked(base.powf(self.unary()?))
        } else {
            Ok(base)
        }
    }

    fn primary(&mut self) -> Result<f64, String> {
        if self.take(b'(') {
            let value = self.additive()?;
            if !self.take(b')') { return Err("expected ')'".into()); }
            Ok(value)
        } else {
            self.number()
        }
    }

    fn number(&mut self) -> Result<f64, String> {
        self.skip_space();
        let start = self.pos;
        let mut digits = 0;
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
        let text = std::str::from_utf8(&self.input[start..self.pos]).map_err(|_| "invalid number")?;
        let value: f64 = text.parse().map_err(|_| "invalid number")?;
        if !value.is_finite() { return Err("non-finite input".into()); }
        Ok(value)
    }
}

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() != 2 {
        eprintln!("error: expected exactly one expression");
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
