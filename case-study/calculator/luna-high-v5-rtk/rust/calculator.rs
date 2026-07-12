use std::env;

struct Parser {
    source: Vec<u8>,
    pos: usize,
}

impl Parser {
    fn new(source: String) -> Self {
        Self { source: source.into_bytes(), pos: 0 }
    }

    fn error(message: &str) -> String {
        format!("error: {message}")
    }

    fn skip_space(&mut self) {
        while self.pos < self.source.len() && matches!(self.source[self.pos], b' ' | b'\t' | b'\n' | b'\r' | 0x0b | 0x0c) {
            self.pos += 1;
        }
    }

    fn take(&mut self, token: u8) -> bool {
        self.skip_space();
        if self.pos < self.source.len() && self.source[self.pos] == token {
            self.pos += 1;
            true
        } else {
            false
        }
    }

    fn parse(&mut self) -> Result<f64, String> {
        let value = self.parse_additive()?;
        self.skip_space();
        if self.pos != self.source.len() {
            return Err(Self::error("trailing tokens"));
        }
        Ok(value)
    }

    fn parse_additive(&mut self) -> Result<f64, String> {
        let mut value = self.parse_multiplicative()?;
        loop {
            if self.take(b'+') {
                value = Self::checked(value + self.parse_multiplicative()?)?;
            } else if self.take(b'-') {
                value = Self::checked(value - self.parse_multiplicative()?)?;
            } else {
                return Ok(value);
            }
        }
    }

    fn parse_multiplicative(&mut self) -> Result<f64, String> {
        let mut value = self.parse_unary()?;
        loop {
            if self.take(b'*') {
                value = Self::checked(value * self.parse_unary()?)?;
            } else if self.take(b'/') {
                let rhs = self.parse_unary()?;
                if rhs == 0.0 { return Err(Self::error("division by zero")); }
                value = Self::checked(value / rhs)?;
            } else if self.take(b'%') {
                let rhs = self.parse_unary()?;
                if rhs == 0.0 { return Err(Self::error("remainder by zero")); }
                value = Self::checked(value % rhs)?;
            } else {
                return Ok(value);
            }
        }
    }

    fn parse_unary(&mut self) -> Result<f64, String> {
        if self.take(b'+') { return self.parse_unary(); }
        if self.take(b'-') { return Self::checked(-self.parse_unary()?); }
        self.parse_power()
    }

    fn parse_power(&mut self) -> Result<f64, String> {
        let value = self.parse_primary()?;
        if self.take(b'^') {
            return Self::checked(value.powf(self.parse_unary()?));
        }
        Ok(value)
    }

    fn parse_primary(&mut self) -> Result<f64, String> {
        self.skip_space();
        if self.take(b'(') {
            let value = self.parse_additive()?;
            if !self.take(b')') { return Err(Self::error("missing closing parenthesis")); }
            return Ok(value);
        }

        let start = self.pos;
        let mut before = 0;
        while self.pos < self.source.len() && self.source[self.pos].is_ascii_digit() {
            self.pos += 1;
            before += 1;
        }
        let mut after = 0;
        if self.pos < self.source.len() && self.source[self.pos] == b'.' {
            self.pos += 1;
            while self.pos < self.source.len() && self.source[self.pos].is_ascii_digit() {
                self.pos += 1;
                after += 1;
            }
        }
        if before == 0 && after == 0 { return Err(Self::error("expected number or parenthesis")); }
        if self.pos < self.source.len() && matches!(self.source[self.pos], b'e' | b'E') {
            self.pos += 1;
            if self.pos < self.source.len() && matches!(self.source[self.pos], b'+' | b'-') { self.pos += 1; }
            let exponent_start = self.pos;
            while self.pos < self.source.len() && self.source[self.pos].is_ascii_digit() { self.pos += 1; }
            if self.pos == exponent_start { return Err(Self::error("invalid exponent")); }
        }

        let token = std::str::from_utf8(&self.source[start..self.pos]).map_err(|_| Self::error("invalid number"))?;
        let value = token.parse::<f64>().map_err(|_| Self::error("invalid number"))?;
        Self::checked(value)
    }

    fn checked(value: f64) -> Result<f64, String> {
        if value.is_finite() { Ok(value) } else { Err(Self::error("non-finite result")) }
    }
}

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() != 2 {
        eprintln!("error: expected exactly one expression");
        std::process::exit(1);
    }
    match Parser::new(args[1].clone()).parse() {
        Ok(value) => println!("{value:.17e}"),
        Err(message) => { eprintln!("{message}"); std::process::exit(1); }
    }
}
