use std::env;
use std::process;

fn fail(message: &str) -> ! {
    eprintln!("error: {}", message);
    process::exit(1);
}

struct Parser {
    input: Vec<u8>,
    pos: usize,
}

impl Parser {
    fn new(text: String) -> Self {
        Self {
            input: text.into_bytes(),
            pos: 0,
        }
    }

    fn parse(&mut self) -> f64 {
        let value = self.parse_add_sub();
        self.skip_ws();
        if self.pos != self.input.len() {
            fail("trailing input");
        }
        self.ensure_finite(value)
    }

    fn parse_add_sub(&mut self) -> f64 {
        let mut value = self.parse_mul_div_mod();
        loop {
            self.skip_ws();
            if self.pos >= self.input.len() {
                break;
            }
            match self.input[self.pos] {
                b'+' => {
                    self.pos += 1;
                    let right = self.parse_mul_div_mod();
                    value = self.ensure_finite(value + right);
                }
                b'-' => {
                    self.pos += 1;
                    let right = self.parse_mul_div_mod();
                    value = self.ensure_finite(value - right);
                }
                _ => break,
            }
        }
        value
    }

    fn parse_mul_div_mod(&mut self) -> f64 {
        let mut value = self.parse_unary();
        loop {
            self.skip_ws();
            if self.pos >= self.input.len() {
                break;
            }
            match self.input[self.pos] {
                b'*' => {
                    self.pos += 1;
                    let right = self.parse_unary();
                    value = self.ensure_finite(value * right);
                }
                b'/' => {
                    self.pos += 1;
                    let right = self.parse_unary();
                    if right == 0.0 {
                        fail("division by zero");
                    }
                    value = self.ensure_finite(value / right);
                }
                b'%' => {
                    self.pos += 1;
                    let right = self.parse_unary();
                    if right == 0.0 {
                        fail("remainder by zero");
                    }
                    value = self.ensure_finite(value % right);
                }
                _ => break,
            }
        }
        value
    }

    fn parse_unary(&mut self) -> f64 {
        self.skip_ws();
        if self.pos >= self.input.len() {
            fail("malformed expression");
        }
        match self.input[self.pos] {
            b'+' => {
                self.pos += 1;
                self.parse_unary()
            }
            b'-' => {
                self.pos += 1;
                let inner = self.parse_unary();
                self.ensure_finite(-inner)
            }
            _ => self.parse_pow(),
        }
    }

    fn parse_pow(&mut self) -> f64 {
        let mut value = self.parse_primary();
        self.skip_ws();
        if self.pos < self.input.len() && self.input[self.pos] == b'^' {
            self.pos += 1;
            let right = self.parse_pow();
            value = self.ensure_finite(value.powf(right));
        }
        value
    }

    fn parse_primary(&mut self) -> f64 {
        self.skip_ws();
        if self.pos >= self.input.len() {
            fail("malformed expression");
        }
        if self.input[self.pos] == b'(' {
            self.pos += 1;
            let value = self.parse_add_sub();
            self.skip_ws();
            if self.pos >= self.input.len() || self.input[self.pos] != b')' {
                fail("missing closing parenthesis");
            }
            self.pos += 1;
            return value;
        }
        self.parse_number()
    }

    fn parse_number(&mut self) -> f64 {
        self.skip_ws();
        if self.pos >= self.input.len() {
            fail("malformed expression");
        }

        let start = self.pos;
        let mut has_exp = false;
        let mut has_dot = false;
        let mut has_digit = false;

        let first = self.input[self.pos];
        if !first.is_ascii_digit() && first != b'.' {
            fail("invalid token");
        }

        if first == b'.' {
            self.pos += 1;
        }

        while self.pos < self.input.len() {
            let ch = self.input[self.pos];
            if ch.is_ascii_digit() {
                self.pos += 1;
                has_digit = true;
                continue;
            }
            if ch == b'.' && !has_dot && !has_exp {
                self.pos += 1;
                has_dot = true;
                continue;
            }
            if (ch == b'e' || ch == b'E') && !has_exp {
                if !has_digit && !has_dot {
                    fail("invalid number");
                }
                has_exp = true;
                self.pos += 1;
                if self.pos < self.input.len() && (self.input[self.pos] == b'+' || self.input[self.pos] == b'-') {
                    self.pos += 1;
                }
                if self.pos >= self.input.len() || !self.input[self.pos].is_ascii_digit() {
                    fail("invalid number");
                }
                while self.pos < self.input.len() && self.input[self.pos].is_ascii_digit() {
                    self.pos += 1;
                }
                break;
            }
            break;
        }

        if self.pos == start {
            fail("invalid number");
        }

        if !has_digit && !has_dot {
            fail("invalid number");
        }

        let token = std::str::from_utf8(&self.input[start..self.pos]).unwrap_or_else(|_| {
            fail("invalid token");
        });
        let value: f64 = token.parse().unwrap_or_else(|_| {
            fail("invalid number");
        });
        if !value.is_finite() {
            fail("non-finite number");
        }
        self.ensure_finite(value)
    }

    fn skip_ws(&mut self) {
        while self.pos < self.input.len() && self.input[self.pos].is_ascii_whitespace() {
            self.pos += 1;
        }
    }

    fn ensure_finite(&self, value: f64) -> f64 {
        if !value.is_finite() {
            fail("non-finite result");
        }
        value
    }
}

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() != 2 {
        fail("expected exactly one argument");
    }

    let mut parser = Parser::new(args[1].clone());
    let result = parser.parse();
    println!("{}", result);
}
