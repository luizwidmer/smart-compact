use std::env;

struct Parser {
    chars: Vec<char>,
    pos: usize,
}

impl Parser {
    fn new(text: String) -> Self {
        Self { chars: text.chars().collect(), pos: 0 }
    }

    fn error<T>(&self, message: &str) -> Result<T, String> {
        Err(message.to_string())
    }

    fn skip_whitespace(&mut self) {
        while self.pos < self.chars.len() && matches!(self.chars[self.pos], ' ' | '\t' | '\n' | '\r' | '\u{000b}' | '\u{000c}') {
            self.pos += 1;
        }
    }

    fn match_token(&mut self, token: char) -> bool {
        self.skip_whitespace();
        if self.pos < self.chars.len() && self.chars[self.pos] == token {
            self.pos += 1;
            true
        } else {
            false
        }
    }

    fn parse_number(&mut self) -> Result<f64, String> {
        self.skip_whitespace();
        let start = self.pos;
        let mut digits = 0;
        while self.pos < self.chars.len() && self.chars[self.pos].is_ascii_digit() {
            self.pos += 1;
            digits += 1;
        }
        if self.pos < self.chars.len() && self.chars[self.pos] == '.' {
            self.pos += 1;
            while self.pos < self.chars.len() && self.chars[self.pos].is_ascii_digit() {
                self.pos += 1;
                digits += 1;
            }
        }
        if digits == 0 {
            return self.error("expected number");
        }
        if self.pos < self.chars.len() && matches!(self.chars[self.pos], 'e' | 'E') {
            self.pos += 1;
            if self.pos < self.chars.len() && matches!(self.chars[self.pos], '+' | '-') {
                self.pos += 1;
            }
            let exponent_start = self.pos;
            while self.pos < self.chars.len() && self.chars[self.pos].is_ascii_digit() {
                self.pos += 1;
            }
            if exponent_start == self.pos {
                return self.error("invalid exponent");
            }
        }
        let token: String = self.chars[start..self.pos].iter().collect();
        match token.parse::<f64>() {
            Ok(value) if value.is_finite() => Ok(value),
            _ => self.error("non-finite number"),
        }
    }

    fn parse_primary(&mut self) -> Result<f64, String> {
        if self.match_token('(') {
            let value = self.parse_expression()?;
            if !self.match_token(')') {
                return self.error("expected ')' ");
            }
            Ok(value)
        } else {
            self.parse_number()
        }
    }

    fn parse_power(&mut self) -> Result<f64, String> {
        let value = self.parse_primary()?;
        if self.match_token('^') {
            let result = value.powf(self.parse_unary()?);
            if !result.is_finite() {
                return self.error("non-finite result");
            }
            Ok(result)
        } else {
            Ok(value)
        }
    }

    fn parse_unary(&mut self) -> Result<f64, String> {
        if self.match_token('+') {
            return self.parse_unary();
        }
        if self.match_token('-') {
            let result = -self.parse_unary()?;
            if !result.is_finite() {
                return self.error("non-finite result");
            }
            return Ok(result);
        }
        self.parse_power()
    }

    fn parse_multiplicative(&mut self) -> Result<f64, String> {
        let mut value = self.parse_unary()?;
        loop {
            if self.match_token('*') {
                value *= self.parse_unary()?;
            } else if self.match_token('/') {
                let divisor = self.parse_unary()?;
                if divisor == 0.0 { return self.error("division by zero"); }
                value /= divisor;
            } else if self.match_token('%') {
                let divisor = self.parse_unary()?;
                if divisor == 0.0 { return self.error("remainder by zero"); }
                value %= divisor;
            } else {
                break;
            }
            if !value.is_finite() { return self.error("non-finite result"); }
        }
        Ok(value)
    }

    fn parse_expression(&mut self) -> Result<f64, String> {
        let mut value = self.parse_multiplicative()?;
        loop {
            if self.match_token('+') {
                value += self.parse_multiplicative()?;
            } else if self.match_token('-') {
                value -= self.parse_multiplicative()?;
            } else {
                break;
            }
            if !value.is_finite() { return self.error("non-finite result"); }
        }
        Ok(value)
    }

    fn parse(&mut self) -> Result<f64, String> {
        let value = self.parse_expression()?;
        self.skip_whitespace();
        if self.pos != self.chars.len() { return self.error("trailing tokens"); }
        Ok(value)
    }
}

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() != 2 {
        eprintln!("error: expected exactly one expression argument");
        std::process::exit(1);
    }
    match Parser::new(args[1].clone()).parse() {
        Ok(value) => println!("{value}"),
        Err(message) => {
            eprintln!("error: {message}");
            std::process::exit(1);
        }
    }
}
