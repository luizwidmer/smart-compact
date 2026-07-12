use std::env;
use std::process;

struct ParseError;

struct Parser {
    input: Vec<u8>,
    position: usize,
}

impl Parser {
    fn new(input: String) -> Self {
        Self {
            input: input.into_bytes(),
            position: 0,
        }
    }

    fn peek(&self) -> Option<u8> {
        self.input.get(self.position).copied()
    }

    fn skip_whitespace(&mut self) {
        while matches!(self.peek(), Some(b' ' | b'\t' | b'\n' | b'\r' | b'\x0b' | b'\x0c')) {
            self.position += 1;
        }
    }

    fn checked(value: f64) -> Result<f64, ParseError> {
        if value.is_finite() {
            Ok(value)
        } else {
            Err(ParseError)
        }
    }

    fn parse(&mut self) -> Result<f64, ParseError> {
        let value = self.parse_additive()?;
        self.skip_whitespace();
        if self.position != self.input.len() {
            return Err(ParseError);
        }
        Ok(value)
    }

    fn parse_additive(&mut self) -> Result<f64, ParseError> {
        let mut left = self.parse_multiplicative()?;
        loop {
            self.skip_whitespace();
            let operator = match self.peek() {
                Some(b'+') => b'+',
                Some(b'-') => b'-',
                _ => return Ok(left),
            };
            self.position += 1;
            let right = self.parse_multiplicative()?;
            let value = if operator == b'+' {
                left + right
            } else {
                left - right
            };
            left = Self::checked(value)?;
        }
    }

    fn parse_multiplicative(&mut self) -> Result<f64, ParseError> {
        let mut left = self.parse_unary()?;
        loop {
            self.skip_whitespace();
            let operator = match self.peek() {
                Some(b'*') => b'*',
                Some(b'/') => b'/',
                Some(b'%') => b'%',
                _ => return Ok(left),
            };
            self.position += 1;
            let right = self.parse_unary()?;
            if (operator == b'/' || operator == b'%') && right == 0.0 {
                return Err(ParseError);
            }
            let value = match operator {
                b'*' => left * right,
                b'/' => left / right,
                _ => left % right,
            };
            left = Self::checked(value)?;
        }
    }

    fn parse_unary(&mut self) -> Result<f64, ParseError> {
        self.skip_whitespace();
        match self.peek() {
            Some(b'+') => {
                self.position += 1;
                self.parse_unary()
            }
            Some(b'-') => {
                self.position += 1;
                let value = -self.parse_unary()?;
                Self::checked(value)
            }
            _ => self.parse_power(),
        }
    }

    fn parse_power(&mut self) -> Result<f64, ParseError> {
        let base = self.parse_primary()?;
        self.skip_whitespace();
        if self.peek() != Some(b'^') {
            return Ok(base);
        }
        self.position += 1;
        let exponent = self.parse_unary()?;
        Self::checked(base.powf(exponent))
    }

    fn parse_primary(&mut self) -> Result<f64, ParseError> {
        self.skip_whitespace();
        if self.peek() == Some(b'(') {
            self.position += 1;
            let value = self.parse_additive()?;
            self.skip_whitespace();
            if self.peek() != Some(b')') {
                return Err(ParseError);
            }
            self.position += 1;
            return Ok(value);
        }
        self.parse_number()
    }

    fn parse_number(&mut self) -> Result<f64, ParseError> {
        self.skip_whitespace();
        let start = self.position;
        let mut has_digit = false;
        while matches!(self.peek(), Some(b'0'..=b'9')) {
            self.position += 1;
            has_digit = true;
        }
        if self.peek() == Some(b'.') {
            self.position += 1;
            while matches!(self.peek(), Some(b'0'..=b'9')) {
                self.position += 1;
                has_digit = true;
            }
        }
        if !has_digit {
            return Err(ParseError);
        }
        if matches!(self.peek(), Some(b'e' | b'E')) {
            self.position += 1;
            if matches!(self.peek(), Some(b'+' | b'-')) {
                self.position += 1;
            }
            let exponent_start = self.position;
            while matches!(self.peek(), Some(b'0'..=b'9')) {
                self.position += 1;
            }
            if self.position == exponent_start {
                return Err(ParseError);
            }
        }
        let literal = std::str::from_utf8(&self.input[start..self.position]).map_err(|_| ParseError)?;
        let value: f64 = literal.parse().map_err(|_| ParseError)?;
        Self::checked(value)
    }
}

fn report_error() -> ! {
    eprintln!("error: invalid expression");
    process::exit(1);
}

fn main() {
    let arguments: Vec<String> = env::args().collect();
    if arguments.len() != 2 {
        report_error();
    }
    let mut parser = Parser::new(arguments[1].clone());
    match parser.parse() {
        Ok(result) => println!("{:.17e}", result),
        Err(_) => report_error(),
    }
}
