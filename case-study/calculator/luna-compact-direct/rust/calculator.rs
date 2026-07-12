use std::env;
use std::process;

struct Parser<'a> {
    input: &'a [u8],
    position: usize,
}

impl<'a> Parser<'a> {
    fn new(text: &'a str) -> Self {
        Self { input: text.as_bytes(), position: 0 }
    }

    fn skip_whitespace(&mut self) {
        while self.position < self.input.len() && self.input[self.position].is_ascii_whitespace() {
            self.position += 1;
        }
    }

    fn take(&mut self, byte: u8) -> bool {
        self.skip_whitespace();
        if self.input.get(self.position) == Some(&byte) {
            self.position += 1;
            true
        } else {
            false
        }
    }

    fn finite(value: f64) -> Result<f64, String> {
        if value.is_finite() {
            Ok(value)
        } else {
            Err("non-finite result".to_owned())
        }
    }

    fn evaluate(&mut self) -> Result<f64, String> {
        let result = self.parse_sum()?;
        self.skip_whitespace();
        if self.position != self.input.len() {
            return Err("unexpected trailing input".to_owned());
        }
        Ok(result)
    }

    fn parse_sum(&mut self) -> Result<f64, String> {
        let mut result = self.parse_product()?;
        loop {
            if self.take(b'+') {
                result = Self::finite(result + self.parse_product()?)?;
            } else if self.take(b'-') {
                result = Self::finite(result - self.parse_product()?)?;
            } else {
                return Ok(result);
            }
        }
    }

    fn parse_product(&mut self) -> Result<f64, String> {
        let mut result = self.parse_unary()?;
        loop {
            if self.take(b'*') {
                result = Self::finite(result * self.parse_unary()?)?;
            } else if self.take(b'/') {
                let divisor = self.parse_unary()?;
                if divisor == 0.0 {
                    return Err("division by zero".to_owned());
                }
                result = Self::finite(result / divisor)?;
            } else if self.take(b'%') {
                let divisor = self.parse_unary()?;
                if divisor == 0.0 {
                    return Err("remainder by zero".to_owned());
                }
                result = Self::finite(result % divisor)?;
            } else {
                return Ok(result);
            }
        }
    }

    fn parse_unary(&mut self) -> Result<f64, String> {
        if self.take(b'+') {
            return self.parse_unary();
        }
        if self.take(b'-') {
            return Self::finite(-self.parse_unary()?);
        }
        self.parse_power()
    }

    fn parse_power(&mut self) -> Result<f64, String> {
        let base = self.parse_primary()?;
        if self.take(b'^') {
            let exponent = self.parse_unary()?;
            return Self::finite(base.powf(exponent));
        }
        Ok(base)
    }

    fn parse_primary(&mut self) -> Result<f64, String> {
        if self.take(b'(') {
            let result = self.parse_sum()?;
            if !self.take(b')') {
                return Err("expected closing parenthesis".to_owned());
            }
            return Ok(result);
        }
        self.parse_number()
    }

    fn parse_number(&mut self) -> Result<f64, String> {
        self.skip_whitespace();
        let start = self.position;
        let mut digit_count = 0;

        while self.input.get(self.position).is_some_and(u8::is_ascii_digit) {
            self.position += 1;
            digit_count += 1;
        }

        if self.input.get(self.position) == Some(&b'.') {
            self.position += 1;
            while self.input.get(self.position).is_some_and(u8::is_ascii_digit) {
                self.position += 1;
                digit_count += 1;
            }
        }

        if digit_count == 0 {
            return Err("expected number".to_owned());
        }

        if matches!(self.input.get(self.position), Some(b'e' | b'E')) {
            self.position += 1;
            if matches!(self.input.get(self.position), Some(b'+' | b'-')) {
                self.position += 1;
            }
            let exponent_start = self.position;
            while self.input.get(self.position).is_some_and(u8::is_ascii_digit) {
                self.position += 1;
            }
            if self.position == exponent_start {
                return Err("malformed exponent".to_owned());
            }
        }

        let token = std::str::from_utf8(&self.input[start..self.position])
            .map_err(|_| "invalid number".to_owned())?;
        let value = token.parse::<f64>().map_err(|_| "invalid number".to_owned())?;
        Self::finite(value)
    }
}

fn main() {
    let arguments: Vec<String> = env::args().collect();
    if arguments.len() != 2 {
        eprintln!("error: expected exactly one expression argument");
        process::exit(1);
    }

    let mut parser = Parser::new(&arguments[1]);
    match parser.evaluate() {
        Ok(result) => println!("{:.17e}", result),
        Err(message) => {
            eprintln!("error: {}", message);
            process::exit(1);
        }
    }
}
