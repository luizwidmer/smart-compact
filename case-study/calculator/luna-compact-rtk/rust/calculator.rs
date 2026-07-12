use std::env;
use std::fmt;

#[derive(Debug)]
struct CalculatorError(String);

impl CalculatorError {
    fn new(message: &str) -> Self {
        Self(message.to_string())
    }
}

impl fmt::Display for CalculatorError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(formatter, "{}", self.0)
    }
}

type CalcResult<T> = Result<T, CalculatorError>;

struct Parser<'a> {
    input: &'a [u8],
    position: usize,
}

impl<'a> Parser<'a> {
    fn new(expression: &'a str) -> Self {
        Self {
            input: expression.as_bytes(),
            position: 0,
        }
    }

    fn parse(&mut self) -> CalcResult<f64> {
        let value = self.parse_addition()?;
        self.skip_whitespace();
        if self.position != self.input.len() {
            return Err(CalculatorError::new("unexpected trailing token"));
        }
        Ok(value)
    }

    fn parse_addition(&mut self) -> CalcResult<f64> {
        let mut value = self.parse_multiplication()?;
        loop {
            if self.consume(b'+') {
                let right = self.parse_multiplication()?;
                value = Self::checked(value + right)?;
            } else if self.consume(b'-') {
                let right = self.parse_multiplication()?;
                value = Self::checked(value - right)?;
            } else {
                return Ok(value);
            }
        }
    }

    fn parse_multiplication(&mut self) -> CalcResult<f64> {
        let mut value = self.parse_unary()?;
        loop {
            if self.consume(b'*') {
                let right = self.parse_unary()?;
                value = Self::checked(value * right)?;
            } else if self.consume(b'/') {
                let right = self.parse_unary()?;
                if right == 0.0 {
                    return Err(CalculatorError::new("division by zero"));
                }
                value = Self::checked(value / right)?;
            } else if self.consume(b'%') {
                let right = self.parse_unary()?;
                if right == 0.0 {
                    return Err(CalculatorError::new("remainder by zero"));
                }
                value = Self::checked(value % right)?;
            } else {
                return Ok(value);
            }
        }
    }

    fn parse_unary(&mut self) -> CalcResult<f64> {
        if self.consume(b'+') {
            return self.parse_unary();
        }
        if self.consume(b'-') {
            return Ok(-self.parse_unary()?);
        }
        self.parse_power()
    }

    fn parse_power(&mut self) -> CalcResult<f64> {
        let value = self.parse_primary()?;
        if self.consume(b'^') {
            let exponent = self.parse_unary()?;
            return Self::checked(value.powf(exponent));
        }
        Ok(value)
    }

    fn parse_primary(&mut self) -> CalcResult<f64> {
        self.skip_whitespace();
        match self.peek() {
            Some(b'(') => {
                self.position += 1;
                let value = self.parse_addition()?;
                if !self.consume(b')') {
                    return Err(CalculatorError::new("missing closing parenthesis"));
                }
                Ok(value)
            }
            Some(byte) if Self::is_digit(byte) || byte == b'.' => self.parse_number(),
            _ => Err(CalculatorError::new(
                "expected a number or parenthesized expression",
            )),
        }
    }

    fn parse_number(&mut self) -> CalcResult<f64> {
        let start = self.position;
        let mut digits_before_decimal = 0;
        while let Some(byte) = self.peek() {
            if !Self::is_digit(byte) {
                break;
            }
            self.position += 1;
            digits_before_decimal += 1;
        }

        let mut digits_after_decimal = 0;
        if self.peek() == Some(b'.') {
            self.position += 1;
            while let Some(byte) = self.peek() {
                if !Self::is_digit(byte) {
                    break;
                }
                self.position += 1;
                digits_after_decimal += 1;
            }
        }

        if digits_before_decimal == 0 && digits_after_decimal == 0 {
            return Err(CalculatorError::new("invalid number"));
        }

        if matches!(self.peek(), Some(b'e' | b'E')) {
            self.position += 1;
            if matches!(self.peek(), Some(b'+' | b'-')) {
                self.position += 1;
            }
            let mut exponent_digits = 0;
            while let Some(byte) = self.peek() {
                if !Self::is_digit(byte) {
                    break;
                }
                self.position += 1;
                exponent_digits += 1;
            }
            if exponent_digits == 0 {
                return Err(CalculatorError::new("invalid exponent"));
            }
        }

        let literal = std::str::from_utf8(&self.input[start..self.position])
            .map_err(|_| CalculatorError::new("invalid number"))?;
        let value = literal
            .parse::<f64>()
            .map_err(|_| CalculatorError::new("invalid number"))?;
        Self::checked(value)
    }

    fn consume(&mut self, token: u8) -> bool {
        self.skip_whitespace();
        if self.peek() == Some(token) {
            self.position += 1;
            true
        } else {
            false
        }
    }

    fn skip_whitespace(&mut self) {
        while let Some(byte) = self.peek() {
            if !Self::is_whitespace(byte) {
                break;
            }
            self.position += 1;
        }
    }

    fn peek(&self) -> Option<u8> {
        self.input.get(self.position).copied()
    }

    fn is_digit(byte: u8) -> bool {
        byte.is_ascii_digit()
    }

    fn is_whitespace(byte: u8) -> bool {
        matches!(byte, b' ' | b'\t' | b'\n' | b'\r' | b'\x0b' | b'\x0c')
    }

    fn checked(value: f64) -> CalcResult<f64> {
        if value.is_finite() {
            Ok(value)
        } else {
            Err(CalculatorError::new("non-finite result"))
        }
    }
}

fn main() {
    let arguments: Vec<String> = env::args().collect();
    if arguments.len() != 2 {
        eprintln!("error: expected exactly one expression argument");
        std::process::exit(1);
    }

    let mut parser = Parser::new(&arguments[1]);
    match parser.parse() {
        Ok(result) => println!("{:.17e}", result),
        Err(error) => {
            eprintln!("error: {}", error);
            std::process::exit(1);
        }
    }
}
