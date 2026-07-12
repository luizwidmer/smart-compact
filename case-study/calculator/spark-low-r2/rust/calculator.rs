use std::env;
use std::io::{self, Write};

struct Parser {
    text: Vec<u8>,
    i: usize,
    n: usize,
}

impl Parser {
    fn new(s: String) -> Self {
        let bytes = s.clone().into_bytes();
        Self { text: bytes, i: 0, n: s.len() }
    }

    fn error(msg: &str) -> ! {
        let _ = writeln!(io::stderr(), "error: {}", msg);
        std::process::exit(1);
    }

    fn skip_ws(&mut self) {
        while self.i < self.n && self.text[self.i].is_ascii_whitespace() {
            self.i += 1;
        }
    }

    fn parse(&mut self) -> f64 {
        let v = self.parse_expr();
        self.skip_ws();
        if self.i != self.n {
            Self::error("unexpected token");
        }
        if !v.is_finite() {
            Self::error("non-finite result");
        }
        v
    }

    fn parse_expr(&mut self) -> f64 {
        let mut v = self.parse_term();
        loop {
            self.skip_ws();
            if self.i >= self.n {
                break;
            }
            let op = self.text[self.i];
            if op != b'+' && op != b'-' {
                break;
            }
            self.i += 1;
            let rhs = self.parse_term();
            v = if op == b'+' { v + rhs } else { v - rhs };
            if !v.is_finite() {
                Self::error("non-finite result");
            }
        }
        v
    }

    fn parse_term(&mut self) -> f64 {
        let mut v = self.parse_unary();
        loop {
            self.skip_ws();
            if self.i >= self.n {
                break;
            }
            let op = self.text[self.i];
            if op != b'*' && op != b'/' && op != b'%' {
                break;
            }
            self.i += 1;
            let rhs = self.parse_unary();
            v = match op {
                b'*' => v * rhs,
                b'/' => {
                    if rhs == 0.0 {
                        Self::error("division by zero");
                    }
                    v / rhs
                }
                _ => {
                    if rhs == 0.0 {
                        Self::error("remainder by zero");
                    }
                    v % rhs
                }
            };
            if !v.is_finite() {
                Self::error("non-finite result");
            }
        }
        v
    }

    fn parse_unary(&mut self) -> f64 {
        self.skip_ws();
        if self.i >= self.n {
            Self::error("unexpected end of input");
        }
        match self.text[self.i] {
            b'+' => {
                self.i += 1;
                self.parse_unary()
            }
            b'-' => {
                self.i += 1;
                -self.parse_unary()
            }
            _ => self.parse_power(),
        }
    }

    fn parse_power(&mut self) -> f64 {
        let mut v = self.parse_primary();
        self.skip_ws();
        if self.i < self.n && self.text[self.i] == b'^' {
            self.i += 1;
            let rhs = self.parse_unary();
            v = v.powf(rhs);
            if !v.is_finite() {
                Self::error("non-finite result");
            }
        }
        v
    }

    fn parse_number(&mut self, start: usize) -> Option<f64> {
        let mut j = start;
        if j >= self.n || self.text[j] == b'+' || self.text[j] == b'-' {
            return None;
        }

        let mut seen_digit = false;

        if self.text[j] == b'.' {
            j += 1;
            if j >= self.n || !self.text[j].is_ascii_digit() {
                return None;
            }
            seen_digit = true;
            while j < self.n && self.text[j].is_ascii_digit() {
                j += 1;
            }
        } else if self.text[j].is_ascii_digit() {
            while j < self.n && self.text[j].is_ascii_digit() {
                j += 1;
                seen_digit = true;
            }
            if j < self.n && self.text[j] == b'.' {
                j += 1;
                while j < self.n && self.text[j].is_ascii_digit() {
                    j += 1;
                }
            }
        } else {
            return None;
        }

        if j < self.n && (self.text[j] == b'e' || self.text[j] == b'E') {
            j += 1;
            if j < self.n && (self.text[j] == b'+' || self.text[j] == b'-') {
                j += 1;
            }
            if j >= self.n || !self.text[j].is_ascii_digit() {
                return None;
            }
            while j < self.n && self.text[j].is_ascii_digit() {
                j += 1;
            }
        }

        if !seen_digit {
            return None;
        }

        let token = match std::str::from_utf8(&self.text[start..j]) {
            Ok(t) => t,
            Err(_) => return None,
        };
        token.parse::<f64>().ok()
    }

    fn parse_primary(&mut self) -> f64 {
        self.skip_ws();
        if self.i >= self.n {
            Self::error("unexpected end of input");
        }
        if self.text[self.i] == b'(' {
            self.i += 1;
            let v = self.parse_expr();
            self.skip_ws();
            if self.i >= self.n || self.text[self.i] != b')' {
                Self::error("missing closing parenthesis");
            }
            self.i += 1;
            return v;
        }
        let start = self.i;
        let v = match self.parse_number(start) {
            Some(num) => num,
            None => Self::error("invalid number"),
        };
        self.i += 0;
        // parse_number uses direct indexing, so update i to end via a second scan
        let mut end = start;
        if end < self.n && self.text[end] == b'.' {
            end += 1;
            while end < self.n && self.text[end].is_ascii_digit() {
                end += 1;
            }
        } else {
            while end < self.n && self.text[end].is_ascii_digit() {
                end += 1;
            }
            if end < self.n && self.text[end] == b'.' {
                end += 1;
                while end < self.n && self.text[end].is_ascii_digit() {
                    end += 1;
                }
            }
        }
        if end < self.n && (self.text[end] == b'e' || self.text[end] == b'E') {
            end += 1;
            if end < self.n && (self.text[end] == b'+' || self.text[end] == b'-') {
                end += 1;
            }
            while end < self.n && self.text[end].is_ascii_digit() {
                end += 1;
            }
        }
        self.i = end;
        v
    }
}

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() != 2 {
        Parser::error("usage: calculator <expression>");
    }

    let mut p = Parser::new(args[1].clone());
    let v = p.parse();
    if !v.is_finite() {
        Parser::error("non-finite result");
    }

    if v == v.trunc() {
        print!("{}\n", v as i64);
    } else {
        print!("{}\n", v);
    }
}
