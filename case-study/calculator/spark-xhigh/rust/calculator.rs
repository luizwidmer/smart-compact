use std::env;
use std::f64;

struct Parser {
    chars: Vec<u8>,
    pos: usize,
}

#[derive(Debug)]
struct ParseError(String);

impl Parser {
    fn new(expression: &str) -> Self {
        Self {
            chars: expression.as_bytes().to_vec(),
            pos: 0,
        }
    }

    fn parse(&mut self) -> Result<f64, ParseError> {
        let value = self.parse_expr()?;
        self.skip_ws();
        if self.pos != self.chars.len() {
            return Err(ParseError("trailing input".into()));
        }
        self.ensure_finite(value)?;
        Ok(value)
    }

    fn parse_expr(&mut self) -> Result<f64, ParseError> {
        let mut left = self.parse_term()?;
        loop {
            self.skip_ws();
            match self.peek() {
                Some(b'+') => {
                    self.pos += 1;
                    let right = self.parse_term()?;
                    left = self.ensure_finite(left + right)?;
                }
                Some(b'-') => {
                    self.pos += 1;
                    let right = self.parse_term()?;
                    left = self.ensure_finite(left - right)?;
                }
                _ => return Ok(left),
            }
        }
    }

    fn parse_term(&mut self) -> Result<f64, ParseError> {
        let mut left = self.parse_pow()?;
        loop {
            self.skip_ws();
            match self.peek() {
                Some(b'*') => {
                    self.pos += 1;
                    let right = self.parse_pow()?;
                    left = self.ensure_finite(left * right)?;
                }
                Some(b'/') => {
                    self.pos += 1;
                    let right = self.parse_pow()?;
                    if right == 0.0 {
                        return Err(ParseError("division by zero".into()));
                    }
                    left = self.ensure_finite(left / right)?;
                }
                Some(b'%') => {
                    self.pos += 1;
                    let right = self.parse_pow()?;
                    if right == 0.0 {
                        return Err(ParseError("remainder by zero".into()));
                    }
                    left = self.ensure_finite(left % right)?;
                }
                _ => return Ok(left),
            }
        }
    }

    fn parse_pow(&mut self) -> Result<f64, ParseError> {
        let left = self.parse_unary()?;
        self.skip_ws();
        if self.consume(b'^') {
            let right = self.parse_pow()?;
            self.ensure_finite(left.powf(right))
        } else {
            Ok(left)
        }
    }

    fn parse_unary(&mut self) -> Result<f64, ParseError> {
        self.skip_ws();
        if self.consume(b'+') {
            return self.parse_unary();
        }
        if self.consume(b'-') {
            let value = self.parse_unary()?;
            return self.ensure_finite(-value);
        }
        self.parse_primary()
    }

    fn parse_primary(&mut self) -> Result<f64, ParseError> {
        self.skip_ws();
        if self.consume(b'(') {
            let value = self.parse_expr()?;
            self.skip_ws();
            if !self.consume(b')') {
                return Err(ParseError("missing ')'".into()));
            }
            return Ok(value);
        }
        if self.peek().is_none() {
            return Err(ParseError("unexpected end of input".into()));
        }
        let ch = self.chars[self.pos];
        if ch.is_ascii_digit() || ch == b'.' {
            return self.parse_number();
        }
        Err(ParseError("unexpected token".into()))
    }

    fn parse_number(&mut self) -> Result<f64, ParseError> {
        self.skip_ws();
        let start = self.pos;
        if start >= self.chars.len() {
            return Err(ParseError("unexpected end of input".into()));
        }
        if self.chars[start] == b'.' {
            if start + 1 >= self.chars.len() || !self.chars[start + 1].is_ascii_digit() {
                return Err(ParseError("invalid number".into()));
            }
        } else if !self.chars[start].is_ascii_digit() {
            return Err(ParseError("invalid number".into()));
        }

        let mut idx = start;
        while idx < self.chars.len() && self.chars[idx].is_ascii_digit() {
            idx += 1;
        }
        if idx < self.chars.len() && self.chars[idx] == b'.' {
            idx += 1;
            while idx < self.chars.len() && self.chars[idx].is_ascii_digit() {
                idx += 1;
            }
        }
        if idx < self.chars.len() && (self.chars[idx] == b'e' || self.chars[idx] == b'E') {
            idx += 1;
            if idx < self.chars.len() && (self.chars[idx] == b'+' || self.chars[idx] == b'-') {
                idx += 1;
            }
            if idx >= self.chars.len() || !self.chars[idx].is_ascii_digit() {
                return Err(ParseError("invalid number".into()));
            }
            while idx < self.chars.len() && self.chars[idx].is_ascii_digit() {
                idx += 1;
            }
        }
        if idx == start {
            return Err(ParseError("invalid number".into()));
        }

        let token = std::str::from_utf8(&self.chars[start..idx]).unwrap_or("");
        self.pos = idx;

        let value = token.parse::<f64>().map_err(|_| ParseError("invalid number".into()))?;
        self.ensure_finite(value)?;
        Ok(value)
    }

    fn skip_ws(&mut self) {
        while self.pos < self.chars.len() && self.chars[self.pos].is_ascii_whitespace() {
            self.pos += 1;
        }
    }

    fn peek(&self) -> Option<u8> {
        self.chars.get(self.pos).copied()
    }

    fn consume(&mut self, expected: u8) -> bool {
        if self.pos < self.chars.len() && self.chars[self.pos] == expected {
            self.pos += 1;
            return true;
        }
        false
    }

    fn ensure_finite(&self, value: f64) -> Result<f64, ParseError> {
        if value.is_finite() {
            Ok(value)
        } else {
            Err(ParseError("non-finite value".into()))
        }
    }
}

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() != 2 {
        eprintln!("error: expected exactly one expression argument");
        std::process::exit(1);
    }
    let mut parser = Parser::new(&args[1]);
    match parser.parse() {
        Ok(value) => {
            println!("{}", value);
            std::process::exit(0);
        }
        Err(ParseError(msg)) => {
            eprintln!("error: {}", msg);
            std::process::exit(1);
        }
    }
}
