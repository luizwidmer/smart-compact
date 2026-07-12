use std::env;
use std::process;

struct Parser {
    input: Vec<u8>,
    pos: usize,
}

impl Parser {
    fn new(input: String) -> Self {
        Self { input: input.into_bytes(), pos: 0 }
    }

    fn fail<T>(&self, message: &str) -> Result<T, String> {
        Err(message.to_string())
    }

    fn skip_space(&mut self) {
        while self.pos < self.input.len() && matches!(self.input[self.pos], b' ' | b'\t' | b'\n' | b'\r' | 0x0b | 0x0c) {
            self.pos += 1;
        }
    }

    fn parse_number(&mut self) -> Result<f64, String> {
        self.skip_space();
        let start = self.pos;
        let mut before = 0;
        while self.pos < self.input.len() && self.input[self.pos].is_ascii_digit() {
            self.pos += 1;
            before += 1;
        }
        let mut after = 0;
        if self.pos < self.input.len() && self.input[self.pos] == b'.' {
            self.pos += 1;
            while self.pos < self.input.len() && self.input[self.pos].is_ascii_digit() {
                self.pos += 1;
                after += 1;
            }
        }
        if before + after == 0 {
            return self.fail("expected number");
        }
        if self.pos < self.input.len() && matches!(self.input[self.pos], b'e' | b'E') {
            self.pos += 1;
            if self.pos < self.input.len() && matches!(self.input[self.pos], b'+' | b'-') {
                self.pos += 1;
            }
            let exponent_start = self.pos;
            while self.pos < self.input.len() && self.input[self.pos].is_ascii_digit() {
                self.pos += 1;
            }
            if self.pos == exponent_start {
                return self.fail("invalid exponent");
            }
        }
        let raw = std::str::from_utf8(&self.input[start..self.pos]).map_err(|_| "invalid number".to_string())?;
        let value = raw.parse::<f64>().map_err(|_| "invalid number".to_string())?;
        if !value.is_finite() { return self.fail("non-finite number"); }
        Ok(value)
    }

    fn parse_primary(&mut self) -> Result<f64, String> {
        self.skip_space();
        if self.pos < self.input.len() && self.input[self.pos] == b'(' {
            self.pos += 1;
            let value = self.parse_additive()?;
            self.skip_space();
            if self.pos >= self.input.len() || self.input[self.pos] != b')' {
                return self.fail("expected ')'");
            }
            self.pos += 1;
            Ok(value)
        } else {
            self.parse_number()
        }
    }

    fn parse_power(&mut self) -> Result<f64, String> {
        let mut value = self.parse_primary()?;
        self.skip_space();
        if self.pos < self.input.len() && self.input[self.pos] == b'^' {
            self.pos += 1;
            let exponent = self.parse_unary()?;
            value = value.powf(exponent);
            if !value.is_finite() { return self.fail("non-finite result"); }
        }
        Ok(value)
    }

    fn parse_unary(&mut self) -> Result<f64, String> {
        self.skip_space();
        if self.pos < self.input.len() && matches!(self.input[self.pos], b'+' | b'-') {
            let negative = self.input[self.pos] == b'-';
            self.pos += 1;
            let value = self.parse_unary()?;
            Ok(if negative { -value } else { value })
        } else {
            self.parse_power()
        }
    }

    fn parse_multiplicative(&mut self) -> Result<f64, String> {
        let mut value = self.parse_unary()?;
        loop {
            self.skip_space();
            if self.pos >= self.input.len() || !matches!(self.input[self.pos], b'*' | b'/' | b'%') { return Ok(value); }
            let operator = self.input[self.pos];
            self.pos += 1;
            let right = self.parse_unary()?;
            if right == 0.0 { return self.fail("division by zero"); }
            value = match operator {
                b'*' => value * right,
                b'/' => value / right,
                _ => value % right,
            };
            if !value.is_finite() { return self.fail("non-finite result"); }
        }
    }

    fn parse_additive(&mut self) -> Result<f64, String> {
        let mut value = self.parse_multiplicative()?;
        loop {
            self.skip_space();
            if self.pos >= self.input.len() || !matches!(self.input[self.pos], b'+' | b'-') { return Ok(value); }
            let operator = self.input[self.pos];
            self.pos += 1;
            let right = self.parse_multiplicative()?;
            value = if operator == b'+' { value + right } else { value - right };
            if !value.is_finite() { return self.fail("non-finite result"); }
        }
    }

    fn parse(&mut self) -> Result<f64, String> {
        let value = self.parse_additive()?;
        self.skip_space();
        if self.pos != self.input.len() { return self.fail("unexpected token"); }
        Ok(value)
    }
}

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() != 2 {
        eprintln!("error: expected exactly one expression");
        process::exit(1);
    }
    match Parser::new(args[1].clone()).parse() {
        Ok(value) => println!("{:.17}", value),
        Err(message) => {
            eprintln!("error: {}", message);
            process::exit(1);
        }
    }
}
