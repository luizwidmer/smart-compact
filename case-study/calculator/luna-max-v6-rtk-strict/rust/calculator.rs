use std::env;
use std::process;

struct Parser<'a> {
    input: &'a [u8],
    position: usize,
}

impl<'a> Parser<'a> {
    fn new(input: &'a str) -> Self {
        Self {
            input: input.as_bytes(),
            position: 0,
        }
    }

    fn parse(&mut self) -> Result<f64, String> {
        let value = self.parse_additive()?;
        self.skip_whitespace();
        if self.position != self.input.len() {
            return Err("trailing tokens".to_string());
        }
        Self::checked(value)
    }

    fn skip_whitespace(&mut self) {
        while let Some(byte) = self.peek_raw() {
            if matches!(byte, b' ' | b'\t' | b'\n' | b'\r' | 0x0c | 0x0b) {
                self.position += 1;
            } else {
                break;
            }
        }
    }

    fn peek_raw(&self) -> Option<u8> {
        self.input.get(self.position).copied()
    }

    fn peek(&mut self) -> Option<u8> {
        self.skip_whitespace();
        self.peek_raw()
    }

    fn checked(value: f64) -> Result<f64, String> {
        if value.is_finite() {
            Ok(value)
        } else {
            Err("non-finite result".to_string())
        }
    }

    fn parse_additive(&mut self) -> Result<f64, String> {
        let mut left = self.parse_multiplicative()?;
        loop {
            let operator = self.peek();
            if !matches!(operator, Some(b'+') | Some(b'-')) {
                return Ok(left);
            }
            self.position += 1;
            let right = self.parse_multiplicative()?;
            let result = if operator == Some(b'+') {
                left + right
            } else {
                left - right
            };
            left = Self::checked(result)?;
        }
    }

    fn parse_multiplicative(&mut self) -> Result<f64, String> {
        let mut left = self.parse_unary()?;
        loop {
            let operator = self.peek();
            if !matches!(operator, Some(b'*') | Some(b'/') | Some(b'%')) {
                return Ok(left);
            }
            self.position += 1;
            let right = self.parse_unary()?;
            if matches!(operator, Some(b'/') | Some(b'%')) && right == 0.0 {
                return Err("division or remainder by zero".to_string());
            }
            let result = match operator {
                Some(b'*') => left * right,
                Some(b'/') => left / right,
                Some(b'%') => left % right,
                _ => unreachable!(),
            };
            left = Self::checked(result)?;
        }
    }

    fn parse_unary(&mut self) -> Result<f64, String> {
        match self.peek() {
            Some(b'+') | Some(b'-') => {
                let operator = self.peek_raw().unwrap();
                self.position += 1;
                let value = self.parse_unary()?;
                Self::checked(if operator == b'+' { value } else { -value })
            }
            _ => self.parse_power(),
        }
    }

    fn parse_power(&mut self) -> Result<f64, String> {
        let base = self.parse_primary()?;
        if self.peek() == Some(b'^') {
            self.position += 1;
            let exponent = self.parse_unary()?;
            Self::checked(base.powf(exponent))
        } else {
            Ok(base)
        }
    }

    fn parse_primary(&mut self) -> Result<f64, String> {
        if self.peek() == Some(b'(') {
            self.position += 1;
            let value = self.parse_additive()?;
            if self.peek() != Some(b')') {
                return Err("missing closing parenthesis".to_string());
            }
            self.position += 1;
            Ok(value)
        } else {
            self.parse_number()
        }
    }

    fn is_digit(byte: u8) -> bool {
        byte.is_ascii_digit()
    }

    fn parse_number(&mut self) -> Result<f64, String> {
        self.skip_whitespace();
        let start = self.position;
        let mut digits_before = 0;
        while self.peek_raw().is_some_and(Self::is_digit) {
            self.position += 1;
            digits_before += 1;
        }

        let mut digits_after = 0;
        if self.peek_raw() == Some(b'.') {
            self.position += 1;
            while self.peek_raw().is_some_and(Self::is_digit) {
                self.position += 1;
                digits_after += 1;
            }
        }

        if digits_before == 0 && digits_after == 0 {
            return Err("expected number or parenthesis".to_string());
        }

        if matches!(self.peek_raw(), Some(b'e') | Some(b'E')) {
            self.position += 1;
            if matches!(self.peek_raw(), Some(b'+') | Some(b'-')) {
                self.position += 1;
            }
            let exponent_start = self.position;
            while self.peek_raw().is_some_and(Self::is_digit) {
                self.position += 1;
            }
            if self.position == exponent_start {
                return Err("malformed exponent".to_string());
            }
        }

        let token = std::str::from_utf8(&self.input[start..self.position])
            .map_err(|_| "invalid number".to_string())?;
        let value = token
            .parse::<f64>()
            .map_err(|_| "invalid number".to_string())?;
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
        Ok(value) => println!("{:.17}", value),
        Err(error) => {
            eprintln!("error: {}", error);
            process::exit(1);
        }
    }
}
