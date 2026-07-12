use std::env;
use std::process;

struct Parser<'a> {
    input: &'a [u8],
    position: usize,
}

impl<'a> Parser<'a> {
    fn new(expression: &'a str) -> Self {
        Self { input: expression.as_bytes(), position: 0 }
    }

    fn checked(value: f64) -> Result<f64, String> {
        if value.is_finite() { Ok(value) } else { Err("non-finite result".into()) }
    }

    fn current(&self) -> Option<u8> { self.input.get(self.position).copied() }

    fn is_digit(byte: u8) -> bool { byte.is_ascii_digit() }

    fn is_whitespace(byte: u8) -> bool {
        matches!(byte, b' ' | b'\t' | b'\r' | b'\n' | b'\x0b' | b'\x0c')
    }

    fn skip_whitespace(&mut self) {
        while let Some(byte) = self.current() {
            if !Self::is_whitespace(byte) { break; }
            self.position += 1;
        }
    }

    fn parse(&mut self) -> Result<f64, String> {
        let value = self.parse_add_sub()?;
        self.skip_whitespace();
        if self.position != self.input.len() { return Err("trailing tokens".into()); }
        Self::checked(value)
    }

    fn parse_add_sub(&mut self) -> Result<f64, String> {
        let mut value = self.parse_mul_div()?;
        loop {
            self.skip_whitespace();
            let operation = match self.current() {
                Some(byte @ (b'+' | b'-')) => byte,
                _ => return Ok(value),
            };
            self.position += 1;
            let right = self.parse_mul_div()?;
            value = Self::checked(if operation == b'+' { value + right } else { value - right })?;
        }
    }

    fn parse_mul_div(&mut self) -> Result<f64, String> {
        let mut value = self.parse_unary()?;
        loop {
            self.skip_whitespace();
            let operation = match self.current() {
                Some(byte @ (b'*' | b'/' | b'%')) => byte,
                _ => return Ok(value),
            };
            self.position += 1;
            let right = self.parse_unary()?;
            if (operation == b'/' || operation == b'%') && right == 0.0 {
                return Err("division or remainder by zero".into());
            }
            value = Self::checked(match operation {
                b'*' => value * right,
                b'/' => value / right,
                _ => value % right,
            })?;
        }
    }

    fn parse_unary(&mut self) -> Result<f64, String> {
        self.skip_whitespace();
        match self.current() {
            Some(b'+') => { self.position += 1; self.parse_unary() }
            Some(b'-') => {
                self.position += 1;
                Self::checked(-self.parse_unary()?)
            }
            _ => self.parse_power(),
        }
    }

    fn parse_power(&mut self) -> Result<f64, String> {
        let base = self.parse_primary()?;
        self.skip_whitespace();
        if self.current() != Some(b'^') { return Ok(base); }
        self.position += 1;
        let exponent = self.parse_unary()?;
        Self::checked(base.powf(exponent))
    }

    fn parse_primary(&mut self) -> Result<f64, String> {
        self.skip_whitespace();
        if self.current() == Some(b'(') {
            self.position += 1;
            let value = self.parse_add_sub()?;
            self.skip_whitespace();
            if self.current() != Some(b')') { return Err("expected ')'".into()); }
            self.position += 1;
            return Ok(value);
        }
        self.parse_number()
    }

    fn parse_number(&mut self) -> Result<f64, String> {
        self.skip_whitespace();
        let start = self.position;
        while self.current().is_some_and(Self::is_digit) { self.position += 1; }
        let digits_before = self.position > start;
        let mut digits_after = false;
        if self.current() == Some(b'.') {
            self.position += 1;
            let fraction_start = self.position;
            while self.current().is_some_and(Self::is_digit) { self.position += 1; }
            digits_after = self.position > fraction_start;
        }
        if !digits_before && !digits_after { return Err("expected number".into()); }

        if matches!(self.current(), Some(b'e' | b'E')) {
            self.position += 1;
            if matches!(self.current(), Some(b'+' | b'-')) { self.position += 1; }
            let exponent_start = self.position;
            while self.current().is_some_and(Self::is_digit) { self.position += 1; }
            if self.position == exponent_start { return Err("invalid exponent".into()); }
        }

        let token = std::str::from_utf8(&self.input[start..self.position])
            .map_err(|_| "invalid number".to_string())?;
        let value = token.parse::<f64>().map_err(|_| "invalid number".to_string())?;
        Self::checked(value)
    }
}

fn main() {
    let arguments: Vec<String> = env::args().collect();
    let result = if arguments.len() != 2 {
        Err("expected exactly one expression argument".to_string())
    } else {
        Parser::new(&arguments[1]).parse()
    };
    match result {
        Ok(value) => println!("{:.17e}", value),
        Err(message) => {
            eprintln!("error: {}", message);
            process::exit(1);
        }
    }
}
