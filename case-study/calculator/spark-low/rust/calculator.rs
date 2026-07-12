use std::env;
use std::f64;

struct Parser {
    s: Vec<u8>,
    i: usize,
}

impl Parser {
    fn new(expr: String) -> Self {
        Self { s: expr.into_bytes(), i: 0 }
    }

    fn skip_ws(&mut self) {
        while self.i < self.s.len() && self.s[self.i].is_ascii_whitespace() {
            self.i += 1;
        }
    }

    fn parse_number(&mut self) -> Result<f64, String> {
        self.skip_ws();
        let start = self.i;
        let mut has_digit = false;

        if self.i < self.s.len() && self.s[self.i] == b'.' {
            self.i += 1;
            while self.i < self.s.len() && self.s[self.i].is_ascii_digit() {
                self.i += 1;
                has_digit = true;
            }
        } else {
            while self.i < self.s.len() && self.s[self.i].is_ascii_digit() {
                self.i += 1;
                has_digit = true;
            }
            if self.i < self.s.len() && self.s[self.i] == b'.' {
                self.i += 1;
                while self.i < self.s.len() && self.s[self.i].is_ascii_digit() {
                    self.i += 1;
                    has_digit = true;
                }
            }
        }

        if !has_digit {
            return Err("invalid number".to_string());
        }

        if self.i < self.s.len() && (self.s[self.i] == b'e' || self.s[self.i] == b'E') {
            self.i += 1;
            if self.i < self.s.len() && (self.s[self.i] == b'+' || self.s[self.i] == b'-') {
                self.i += 1;
            }
            if self.i >= self.s.len() || !self.s[self.i].is_ascii_digit() {
                return Err("invalid exponent".to_string());
            }
            while self.i < self.s.len() && self.s[self.i].is_ascii_digit() {
                self.i += 1;
            }
        }

        let token = std::str::from_utf8(&self.s[start..self.i]).map_err(|_| "invalid utf-8".to_string())?;
        let value: f64 = token.parse::<f64>().map_err(|_| "invalid number".to_string())?;
        Ok(value)
    }

    fn parse_expr(&mut self) -> Result<f64, String> {
        let mut value = self.parse_term()?;
        loop {
            self.skip_ws();
            if self.i >= self.s.len() {
                return Ok(value);
            }
            let ch = self.s[self.i];
            if ch != b'+' && ch != b'-' {
                return Ok(value);
            }
            self.i += 1;
            let rhs = self.parse_term()?;
            if ch == b'+' { value += rhs; } else { value -= rhs; }
        }
    }

    fn parse_term(&mut self) -> Result<f64, String> {
        let mut value = self.parse_power()?;
        loop {
            self.skip_ws();
            if self.i >= self.s.len() {
                return Ok(value);
            }
            let ch = self.s[self.i];
            if ch != b'*' && ch != b'/' && ch != b'%' {
                return Ok(value);
            }
            self.i += 1;
            let rhs = self.parse_power()?;
            match ch {
                b'*' => value *= rhs,
                b'/' => {
                    if rhs == 0.0 { return Err("division by zero".to_string()); }
                    value /= rhs;
                }
                b'%' => {
                    if rhs == 0.0 { return Err("remainder by zero".to_string()); }
                    value %= rhs;
                }
                _ => {}
            }
            if !value.is_finite() {
                return Err("non-finite result".to_string());
            }
        }
    }

    fn parse_power(&mut self) -> Result<f64, String> {
        let left = self.parse_unary()?;
        self.skip_ws();
        if self.i >= self.s.len() || self.s[self.i] != b'^' {
            return Ok(left);
        }
        self.i += 1;
        let right = self.parse_power()?;
        Ok(left.powf(right))
    }

    fn parse_unary(&mut self) -> Result<f64, String> {
        self.skip_ws();
        if self.i >= self.s.len() {
            return Err("unexpected end".to_string());
        }
        let ch = self.s[self.i];
        if ch == b'+' || ch == b'-' {
            self.i += 1;
            let v = self.parse_unary()?;
            return Ok(if ch == b'-' { -v } else { v });
        }
        self.parse_primary()
    }

    fn parse_primary(&mut self) -> Result<f64, String> {
        self.skip_ws();
        if self.i >= self.s.len() {
            return Err("unexpected end".to_string());
        }
        if self.s[self.i] == b'(' {
            self.i += 1;
            let v = self.parse_expr()?;
            self.skip_ws();
            if self.i >= self.s.len() || self.s[self.i] != b')' {
                return Err("missing closing paren".to_string());
            }
            self.i += 1;
            return Ok(v);
        }
        self.parse_number()
    }
}

fn evaluate(expr: String) -> Result<f64, String> {
    let mut p = Parser::new(expr);
    p.skip_ws();
    if p.i >= p.s.len() {
        return Err("empty expression".to_string());
    }
    let value = p.parse_expr()?;
    p.skip_ws();
    if p.i != p.s.len() {
        return Err("trailing tokens".to_string());
    }
    if !value.is_finite() {
        return Err("non-finite result".to_string());
    }
    Ok(value)
}

fn main() {
    let mut args = env::args().collect::<Vec<_>>();
    if args.len() != 2 {
        eprintln!("error: expected exactly one expression");
        std::process::exit(1);
    }
    match evaluate(args.remove(1)) {
        Ok(value) => {
            println!("{}", value);
            std::process::exit(0);
        }
        Err(msg) => {
            eprintln!("error: {}", msg);
            std::process::exit(2);
        }
    }
}
