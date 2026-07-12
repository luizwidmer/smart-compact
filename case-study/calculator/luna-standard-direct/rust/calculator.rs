use std::env;
use std::process;

struct Parser<'a> {
    input: &'a [u8],
    position: usize,
}

impl<'a> Parser<'a> {
    fn new(input: &'a [u8]) -> Self {
        Self { input, position: 0 }
    }

    fn skip_whitespace(&mut self) {
        while self.position < self.input.len() && Self::is_ascii_whitespace(self.input[self.position]) {
            self.position += 1;
        }
    }

    fn is_ascii_whitespace(byte: u8) -> bool {
        (9..=13).contains(&byte) || byte == b' '
    }

    fn peek(&self) -> Option<u8> {
        self.input.get(self.position).copied()
    }

    fn checked(value: f64, message: &str) -> Result<f64, String> {
        if value.is_finite() {
            Ok(value)
        } else {
            Err(message.to_string())
        }
    }

    fn parse(&mut self) -> Result<f64, String> {
        let value = self.parse_additive()?;
        self.skip_whitespace();
        if self.position != self.input.len() {
            return Err("unexpected trailing token".to_string());
        }
        Self::checked(value, "non-finite result")
    }

    fn parse_additive(&mut self) -> Result<f64, String> {
        let mut value = self.parse_multiplicative()?;
        loop {
            self.skip_whitespace();
            let operator = match self.peek() {
                Some(b'+') | Some(b'-') => self.peek().unwrap(),
                _ => return Ok(value),
            };
            self.position += 1;
            let right = self.parse_multiplicative()?;
            value = if operator == b'+' { value + right } else { value - right };
            value = Self::checked(value, "non-finite result")?;
        }
    }

    fn parse_multiplicative(&mut self) -> Result<f64, String> {
        let mut value = self.parse_unary()?;
        loop {
            self.skip_whitespace();
            let operator = match self.peek() {
                Some(b'*') | Some(b'/') | Some(b'%') => self.peek().unwrap(),
                _ => return Ok(value),
            };
            self.position += 1;
            let right = self.parse_unary()?;
            value = match operator {
                b'/' => {
                    if right == 0.0 {
                        return Err("division by zero".to_string());
                    }
                    value / right
                }
                b'%' => {
                    if right == 0.0 {
                        return Err("remainder by zero".to_string());
                    }
                    value % right
                }
                _ => value * right,
            };
            value = Self::checked(value, "non-finite result")?;
        }
    }

    fn parse_unary(&mut self) -> Result<f64, String> {
        self.skip_whitespace();
        match self.peek() {
            Some(b'+') => {
                self.position += 1;
                Self::checked(self.parse_unary()?, "non-finite result")
            }
            Some(b'-') => {
                self.position += 1;
                Self::checked(-self.parse_unary()?, "non-finite result")
            }
            _ => self.parse_power(),
        }
    }

    fn parse_power(&mut self) -> Result<f64, String> {
        let left = self.parse_primary()?;
        self.skip_whitespace();
        if self.peek() != Some(b'^') {
            return Ok(left);
        }
        self.position += 1;
        let right = self.parse_unary()?;
        Self::checked(left.powf(right), "non-finite result")
    }

    fn parse_primary(&mut self) -> Result<f64, String> {
        self.skip_whitespace();
        if self.peek() == Some(b'(') {
            self.position += 1;
            let value = self.parse_additive()?;
            self.skip_whitespace();
            if self.peek() != Some(b')') {
                return Err("expected ')'".to_string());
            }
            self.position += 1;
            return Ok(value);
        }
        if matches!(self.peek(), Some(b'0'..=b'9') | Some(b'.')) {
            return self.parse_number();
        }
        Err("expected number or '('".to_string())
    }

    fn parse_number(&mut self) -> Result<f64, String> {
        let start = self.position;
        let mut digits = 0;
        while matches!(self.peek(), Some(b'0'..=b'9')) {
            self.position += 1;
            digits += 1;
        }
        if self.peek() == Some(b'.') {
            self.position += 1;
            while matches!(self.peek(), Some(b'0'..=b'9')) {
                self.position += 1;
                digits += 1;
            }
        }
        if digits == 0 {
            return Err("expected digits".to_string());
        }
        if matches!(self.peek(), Some(b'e') | Some(b'E')) {
            self.position += 1;
            if matches!(self.peek(), Some(b'+') | Some(b'-')) {
                self.position += 1;
            }
            let exponent_start = self.position;
            while matches!(self.peek(), Some(b'0'..=b'9')) {
                self.position += 1;
            }
            if self.position == exponent_start {
                return Err("expected exponent digits".to_string());
            }
        }

        let literal = std::str::from_utf8(&self.input[start..self.position])
            .map_err(|_| "invalid number".to_string())?;
        let value = literal
            .parse::<f64>()
            .map_err(|_| "invalid number".to_string())?;
        Self::checked(value, "non-finite input")
    }
}

fn main() {
    let arguments: Vec<String> = env::args().skip(1).collect();
    if arguments.len() != 1 {
        eprintln!("error: expected exactly one expression argument");
        process::exit(1);
    }

    let mut parser = Parser::new(arguments[0].as_bytes());
    match parser.parse() {
        Ok(result) => println!("{:.17e}", result),
        Err(message) => {
            eprintln!("error: {}", message);
            process::exit(1);
        }
    }
}
