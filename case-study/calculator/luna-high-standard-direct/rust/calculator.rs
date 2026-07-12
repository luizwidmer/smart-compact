use std::env;

struct Parser {
    text: Vec<u8>,
    pos: usize,
}

impl Parser {
    fn new(text: String) -> Self {
        Self {
            text: text.into_bytes(),
            pos: 0,
        }
    }

    fn skip_space(&mut self) {
        while self.pos < self.text.len()
            && matches!(self.text[self.pos], b' ' | b'\t' | b'\n' | b'\r' | 0x0b | 0x0c)
        {
            self.pos += 1;
        }
    }

    fn consume(&mut self, token: u8) -> bool {
        self.skip_space();
        if self.pos < self.text.len() && self.text[self.pos] == token {
            self.pos += 1;
            true
        } else {
            false
        }
    }

    fn finite(value: f64) -> Result<f64, String> {
        if value.is_finite() {
            Ok(value)
        } else {
            Err("non-finite input or result".to_string())
        }
    }

    fn parse(&mut self) -> Result<f64, String> {
        let value = self.parse_additive()?;
        self.skip_space();
        if self.pos != self.text.len() {
            return Err("unexpected trailing input".to_string());
        }
        Ok(value)
    }

    fn parse_additive(&mut self) -> Result<f64, String> {
        let mut value = self.parse_multiplicative()?;
        loop {
            if self.consume(b'+') {
                value = Self::finite(value + self.parse_multiplicative()?)?;
            } else if self.consume(b'-') {
                value = Self::finite(value - self.parse_multiplicative()?)?;
            } else {
                return Ok(value);
            }
        }
    }

    fn parse_multiplicative(&mut self) -> Result<f64, String> {
        let mut value = self.parse_unary()?;
        loop {
            if self.consume(b'*') {
                value = Self::finite(value * self.parse_unary()?)?;
            } else if self.consume(b'/') {
                let divisor = self.parse_unary()?;
                if divisor == 0.0 {
                    return Err("division by zero".to_string());
                }
                value = Self::finite(value / divisor)?;
            } else if self.consume(b'%') {
                let divisor = self.parse_unary()?;
                if divisor == 0.0 {
                    return Err("remainder by zero".to_string());
                }
                value = Self::finite(value % divisor)?;
            } else {
                return Ok(value);
            }
        }
    }

    fn parse_unary(&mut self) -> Result<f64, String> {
        if self.consume(b'+') {
            return self.parse_unary();
        }
        if self.consume(b'-') {
            return Self::finite(-self.parse_unary()?);
        }
        self.parse_power()
    }

    fn parse_power(&mut self) -> Result<f64, String> {
        let value = self.parse_primary()?;
        if self.consume(b'^') {
            let exponent = self.parse_unary()?;
            return Self::finite(value.powf(exponent));
        }
        Ok(value)
    }

    fn parse_primary(&mut self) -> Result<f64, String> {
        if self.consume(b'(') {
            let value = self.parse_additive()?;
            if !self.consume(b')') {
                return Err("expected closing parenthesis".to_string());
            }
            return Ok(value);
        }
        self.parse_number()
    }

    fn parse_number(&mut self) -> Result<f64, String> {
        self.skip_space();
        let start = self.pos;
        let mut digits = 0;
        while self.pos < self.text.len() && self.text[self.pos].is_ascii_digit() {
            self.pos += 1;
            digits += 1;
        }
        if self.pos < self.text.len() && self.text[self.pos] == b'.' {
            self.pos += 1;
            while self.pos < self.text.len() && self.text[self.pos].is_ascii_digit() {
                self.pos += 1;
                digits += 1;
            }
        }
        if digits == 0 {
            return Err("expected number".to_string());
        }
        if self.pos < self.text.len() && matches!(self.text[self.pos], b'e' | b'E') {
            self.pos += 1;
            if self.pos < self.text.len() && matches!(self.text[self.pos], b'+' | b'-') {
                self.pos += 1;
            }
            let exponent_start = self.pos;
            while self.pos < self.text.len() && self.text[self.pos].is_ascii_digit() {
                self.pos += 1;
            }
            if self.pos == exponent_start {
                return Err("malformed exponent".to_string());
            }
        }
        let token = std::str::from_utf8(&self.text[start..self.pos]).unwrap();
        match token.parse::<f64>() {
            Ok(value) => Self::finite(value),
            Err(_) => Err("invalid number".to_string()),
        }
    }
}

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() != 2 {
        eprintln!("error: expected exactly one expression argument");
        std::process::exit(1);
    }
    match Parser::new(args[1].clone()).parse() {
        Ok(result) => println!("{:.17e}", result),
        Err(message) => {
            eprintln!("error: {message}");
            std::process::exit(1);
        }
    }
}
