use std::env;
use std::process;

struct Parser {
    s: Vec<u8>,
    pos: usize,
    n: usize,
}

impl Parser {
    fn new(input: &str) -> Self {
        Self {
            s: input.as_bytes().to_vec(),
            pos: 0,
            n: input.len(),
        }
    }

    fn parse(&mut self) -> Result<f64, String> {
        let value = self.parse_expression()?;
        self.skip_ws();
        if self.pos != self.n {
            return Err("unexpected trailing token".into());
        }
        self.ensure_finite(value)
    }

    fn parse_expression(&mut self) -> Result<f64, String> {
        let mut value = self.parse_term()?;
        loop {
            self.skip_ws();
            if self.consume(b'+') {
                let rhs = self.parse_term()?;
                value = self.ensure_finite(value + rhs)?;
            } else if self.consume(b'-') {
                let rhs = self.parse_term()?;
                value = self.ensure_finite(value - rhs)?;
            } else {
                return Ok(value);
            }
        }
    }

    fn parse_term(&mut self) -> Result<f64, String> {
        let mut value = self.parse_power()?;
        loop {
            self.skip_ws();
            if self.consume(b'*') {
                let rhs = self.parse_power()?;
                value = self.ensure_finite(value * rhs)?;
            } else if self.consume(b'/') {
                let rhs = self.parse_power()?;
                if rhs == 0.0 {
                    return Err("division by zero".into());
                }
                value = self.ensure_finite(value / rhs)?;
            } else if self.consume(b'%') {
                let rhs = self.parse_power()?;
                if rhs == 0.0 {
                    return Err("remainder by zero".into());
                }
                value = self.ensure_finite(value % rhs)?;
            } else {
                return Ok(value);
            }
        }
    }

    fn parse_power(&mut self) -> Result<f64, String> {
        let left = self.parse_unary()?;
        self.skip_ws();
        if self.consume(b'^') {
            let right = self.parse_power()?;
            let value = left.powf(right);
            self.ensure_finite(value)
        } else {
            self.ensure_finite(left)
        }
    }

    fn parse_unary(&mut self) -> Result<f64, String> {
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

    fn parse_primary(&mut self) -> Result<f64, String> {
        self.skip_ws();
        if self.consume(b'(') {
            let value = self.parse_expression()?;
            self.skip_ws();
            if !self.consume(b')') {
                return Err("missing closing parenthesis".into());
            }
            return self.ensure_finite(value);
        }
        self.parse_number()
    }

    fn parse_number(&mut self) -> Result<f64, String> {
        self.skip_ws();
        let start = self.pos;

        if self.pos >= self.n {
            return Err("expected number".into());
        }

        if self.s[self.pos] == b'.' {
            self.pos += 1;
            if self.pos >= self.n || !self.s[self.pos].is_ascii_digit() {
                return Err("invalid number".into());
            }
            while self.pos < self.n && self.s[self.pos].is_ascii_digit() {
                self.pos += 1;
            }
        } else if self.s[self.pos].is_ascii_digit() {
            while self.pos < self.n && self.s[self.pos].is_ascii_digit() {
                self.pos += 1;
            }
            if self.pos < self.n && self.s[self.pos] == b'.' {
                self.pos += 1;
                while self.pos < self.n && self.s[self.pos].is_ascii_digit() {
                    self.pos += 1;
                }
            }
        } else {
            return Err("invalid number".into());
        }

        if self.pos < self.n && (self.s[self.pos] == b'e' || self.s[self.pos] == b'E') {
            self.pos += 1;
            if self.pos < self.n && (self.s[self.pos] == b'+' || self.s[self.pos] == b'-') {
                self.pos += 1;
            }
            if self.pos >= self.n || !self.s[self.pos].is_ascii_digit() {
                return Err("invalid scientific notation".into());
            }
            while self.pos < self.n && self.s[self.pos].is_ascii_digit() {
                self.pos += 1;
            }
        }

        let token = std::str::from_utf8(&self.s[start..self.pos]).map_err(|_| "invalid number")?;
        let value: f64 = token.parse().map_err(|_| "invalid number")?;
        self.ensure_finite(value)
    }

    fn skip_ws(&mut self) {
        while self.pos < self.n && self.s[self.pos].is_ascii_whitespace() {
            self.pos += 1;
        }
    }

    fn consume(&mut self, ch: u8) -> bool {
        if self.pos < self.n && self.s[self.pos] == ch {
            self.pos += 1;
            true
        } else {
            false
        }
    }

    fn ensure_finite(&self, value: f64) -> Result<f64, String> {
        if value.is_finite() {
            Ok(value)
        } else {
            Err("result is not finite".into())
        }
    }
}

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() != 2 {
        eprintln!("error: expected one expression argument");
        process::exit(1);
    }

    let mut parser = Parser::new(&args[1]);
    match parser.parse() {
        Ok(value) => println!("{}", value),
        Err(err) => {
            eprintln!("error: {}", err);
            process::exit(1);
        }
    }
}
