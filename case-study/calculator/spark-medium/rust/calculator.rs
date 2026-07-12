use std::env;
use std::f64;

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() != 2 {
        eprintln!("error: expected exactly one expression argument");
        std::process::exit(1);
    }

    let expr = &args[1];
    let mut p = Parser::new(expr);
    match p.parse() {
        Ok(v) => {
            let out = if v == -0.0 { 0.0 } else { v };
            println!("{:.17}", out);
        }
        Err(msg) => {
            eprintln!("error: {}", msg);
            std::process::exit(1);
        }
    }
}

struct Parser {
    s: Vec<u8>,
    i: usize,
    n: usize,
}

impl Parser {
    fn new(expr: &str) -> Self {
        Self {
            s: expr.as_bytes().to_vec(),
            i: 0,
            n: expr.len(),
        }
    }

    fn parse(&mut self) -> Result<f64, String> {
        let value = self.parse_expr()?;
        self.skip_ws();
        if self.i != self.n {
            return Err("trailing tokens".into());
        }
        if !value.is_finite() {
            return Err("non-finite result".into());
        }
        Ok(value)
    }

    fn parse_expr(&mut self) -> Result<f64, String> {
        self.parse_add()
    }

    fn parse_add(&mut self) -> Result<f64, String> {
        let mut value = self.parse_mul()?;
        loop {
            self.skip_ws();
            if self.match_char(b'+') {
                let rhs = self.parse_mul()?;
                value += rhs;
                self.ensure_finite(value)?;
            } else if self.match_char(b'-') {
                let rhs = self.parse_mul()?;
                value -= rhs;
                self.ensure_finite(value)?;
            } else {
                break;
            }
        }
        Ok(value)
    }

    fn parse_mul(&mut self) -> Result<f64, String> {
        let mut value = self.parse_unary()?;
        loop {
            self.skip_ws();
            if self.match_char(b'*') {
                let rhs = self.parse_unary()?;
                value *= rhs;
                self.ensure_finite(value)?;
            } else if self.match_char(b'/') {
                let rhs = self.parse_unary()?;
                if rhs == 0.0 {
                    return Err("division by zero".into());
                }
                value /= rhs;
                self.ensure_finite(value)?;
            } else if self.match_char(b'%') {
                let rhs = self.parse_unary()?;
                if rhs == 0.0 {
                    return Err("remainder by zero".into());
                }
                value = value % rhs;
                self.ensure_finite(value)?;
            } else {
                break;
            }
        }
        Ok(value)
    }

    fn parse_unary(&mut self) -> Result<f64, String> {
        self.skip_ws();
        if self.match_char(b'+') {
            return self.parse_unary();
        }
        if self.match_char(b'-') {
            return Ok(-self.parse_unary()?);
        }
        self.parse_pow()
    }

    fn parse_pow(&mut self) -> Result<f64, String> {
        let left = self.parse_primary()?;
        self.skip_ws();
        if self.match_char(b'^') {
            let right = self.parse_pow()?;
            let value = left.powf(right);
            self.ensure_finite(value)?;
            Ok(value)
        } else {
            Ok(left)
        }
    }

    fn parse_primary(&mut self) -> Result<f64, String> {
        self.skip_ws();
        if self.match_char(b'(') {
            let value = self.parse_expr()?;
            self.skip_ws();
            if !self.match_char(b')') {
                return Err("missing closing parenthesis".into());
            }
            self.skip_ws();
            return Ok(value);
        }
        self.parse_number()
    }

    fn parse_number(&mut self) -> Result<f64, String> {
        self.skip_ws();
        let start = self.i;
        let mut saw_digit = false;
        let mut saw_dot = false;

        while self.i < self.n && self.s[self.i].is_ascii_digit() {
            self.i += 1;
            saw_digit = true;
        }

        if self.i < self.n && self.s[self.i] == b'.' {
            saw_dot = true;
            self.i += 1;
            while self.i < self.n && self.s[self.i].is_ascii_digit() {
                self.i += 1;
                saw_digit = true;
            }
        }

        if !saw_digit && !saw_dot {
            return Err("expected number".into());
        }

        if self.i < self.n && (self.s[self.i] == b'e' || self.s[self.i] == b'E') {
            self.i += 1;
            if self.i < self.n && (self.s[self.i] == b'+' || self.s[self.i] == b'-') {
                self.i += 1;
            }
            if self.i >= self.n || !self.s[self.i].is_ascii_digit() {
                return Err("invalid exponent".into());
            }
            while self.i < self.n && self.s[self.i].is_ascii_digit() {
                self.i += 1;
            }
        }

        let token = std::str::from_utf8(&self.s[start..self.i]).unwrap();
        let value = token.parse::<f64>().map_err(|_| "invalid number".to_string())?;
        if !value.is_finite() {
            return Err("non-finite literal".into());
        }
        Ok(value)
    }

    fn skip_ws(&mut self) {
        while self.i < self.n && (self.s[self.i] as char).is_whitespace() {
            self.i += 1;
        }
    }

    fn match_char(&mut self, ch: u8) -> bool {
        if self.i < self.n && self.s[self.i] == ch {
            self.i += 1;
            true
        } else {
            false
        }
    }

    fn ensure_finite(&self, v: f64) -> Result<(), String> {
        if !v.is_finite() {
            Err("non-finite result".into())
        } else {
            Ok(())
        }
    }
}
