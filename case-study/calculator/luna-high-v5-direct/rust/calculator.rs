use std::env;

struct Parser<'a> {
    source: &'a [u8],
    pos: usize,
}

impl<'a> Parser<'a> {
    fn new(source: &'a str) -> Self {
        Self { source: source.as_bytes(), pos: 0 }
    }

    fn skip_space(&mut self) {
        while self.pos < self.source.len() && self.source[self.pos].is_ascii_whitespace() {
            self.pos += 1;
        }
    }

    fn take(&mut self, character: u8) -> bool {
        self.skip_space();
        if self.pos < self.source.len() && self.source[self.pos] == character {
            self.pos += 1;
            true
        } else {
            false
        }
    }

    fn parse(&mut self) -> Result<f64, String> {
        let result = self.parse_additive()?;
        self.skip_space();
        if self.pos != self.source.len() {
            return Err("trailing tokens".to_string());
        }
        Ok(result)
    }

    fn parse_additive(&mut self) -> Result<f64, String> {
        let mut result = self.parse_multiplicative()?;
        loop {
            if self.take(b'+') {
                result = checked(result + self.parse_multiplicative()?)?;
            } else if self.take(b'-') {
                result = checked(result - self.parse_multiplicative()?)?;
            } else {
                return Ok(result);
            }
        }
    }

    fn parse_multiplicative(&mut self) -> Result<f64, String> {
        let mut result = self.parse_unary()?;
        loop {
            if self.take(b'*') {
                result = checked(result * self.parse_unary()?)?;
            } else if self.take(b'/') {
                let right = self.parse_unary()?;
                if right == 0.0 { return Err("division by zero".to_string()); }
                result = checked(result / right)?;
            } else if self.take(b'%') {
                let right = self.parse_unary()?;
                if right == 0.0 { return Err("remainder by zero".to_string()); }
                result = checked(result % right)?;
            } else {
                return Ok(result);
            }
        }
    }

    fn parse_unary(&mut self) -> Result<f64, String> {
        if self.take(b'+') { return self.parse_unary(); }
        if self.take(b'-') { return checked(-self.parse_unary()?); }
        self.parse_power()
    }

    fn parse_power(&mut self) -> Result<f64, String> {
        let result = self.parse_primary()?;
        if self.take(b'^') {
            let exponent = self.parse_unary()?;
            return checked(result.powf(exponent));
        }
        Ok(result)
    }

    fn parse_primary(&mut self) -> Result<f64, String> {
        if self.take(b'(') {
            let result = self.parse_additive()?;
            if !self.take(b')') { return Err("expected ')'".to_string()); }
            return Ok(result);
        }

        self.skip_space();
        let start = self.pos;
        while self.pos < self.source.len() && self.source[self.pos].is_ascii_digit() { self.pos += 1; }
        if self.pos < self.source.len() && self.source[self.pos] == b'.' {
            self.pos += 1;
            while self.pos < self.source.len() && self.source[self.pos].is_ascii_digit() { self.pos += 1; }
        } else if start == self.pos && self.pos < self.source.len() && self.source[self.pos] == b'.' {
            self.pos += 1;
            let fraction_start = self.pos;
            while self.pos < self.source.len() && self.source[self.pos].is_ascii_digit() { self.pos += 1; }
            if fraction_start == self.pos { return Err("expected number or '('".to_string()); }
        }
        if start == self.pos { return Err("expected number or '('".to_string()); }
        if self.pos < self.source.len() && (self.source[self.pos] == b'e' || self.source[self.pos] == b'E') {
            self.pos += 1;
            if self.pos < self.source.len() && (self.source[self.pos] == b'+' || self.source[self.pos] == b'-') { self.pos += 1; }
            let exponent_start = self.pos;
            while self.pos < self.source.len() && self.source[self.pos].is_ascii_digit() { self.pos += 1; }
            if exponent_start == self.pos { return Err("invalid exponent".to_string()); }
        }
        let text = std::str::from_utf8(&self.source[start..self.pos]).unwrap();
        checked(text.parse::<f64>().map_err(|_| "invalid number".to_string())?)
    }
}

fn checked(value: f64) -> Result<f64, String> {
    if value.is_finite() { Ok(value) } else { Err("non-finite result".to_string()) }
}

fn main() {
    let arguments: Vec<String> = env::args().collect();
    if arguments.len() != 2 {
        eprintln!("error: expected exactly one expression");
        std::process::exit(1);
    }
    match Parser::new(&arguments[1]).parse() {
        Ok(result) => println!("{}", result),
        Err(error) => {
            eprintln!("error: {}", error);
            std::process::exit(1);
        }
    }
}
