use std::env;

#[derive(Debug)]
struct ParseError(&'static str);

struct Parser {
    expr: Vec<char>,
    pos: usize,
    len: usize,
}

impl Parser {
    fn new(expr: &str) -> Self {
        let chars: Vec<char> = expr.chars().collect();
        let len = chars.len();
        Parser {
            expr: chars,
            pos: 0,
            len,
        }
    }

    fn parse(self) -> Result<f64, ParseError> {
        let mut p = self;
        let value = p.parse_add_sub()?;
        p.skip_ws();
        if p.pos != p.len {
            return Err(ParseError("unexpected token"));
        }
        if !value.is_finite() {
            return Err(ParseError("non-finite result"));
        }
        Ok(value)
    }

    fn parse_add_sub(&mut self) -> Result<f64, ParseError> {
        let mut value = self.parse_mul_div()?;
        loop {
            self.skip_ws();
            if self.consume('+') {
                value += self.parse_mul_div()?;
            } else if self.consume('-') {
                value -= self.parse_mul_div()?;
            } else {
                break;
            }
        }
        Ok(value)
    }

    fn parse_mul_div(&mut self) -> Result<f64, ParseError> {
        let mut value = self.parse_unary()?;
        loop {
            self.skip_ws();
            if self.consume('*') {
                value *= self.parse_unary()?;
            } else if self.consume('/') {
                let rhs = self.parse_unary()?;
                if rhs == 0.0 {
                    return Err(ParseError("division by zero"));
                }
                value /= rhs;
            } else if self.consume('%') {
                let rhs = self.parse_unary()?;
                if rhs == 0.0 {
                    return Err(ParseError("remainder by zero"));
                }
                value %= rhs;
            } else {
                break;
            }
        }
        Ok(value)
    }

    fn parse_unary(&mut self) -> Result<f64, ParseError> {
        self.skip_ws();
        if self.consume('+') {
            return self.parse_unary();
        }
        if self.consume('-') {
            return Ok(-self.parse_unary()?);
        }
        self.parse_pow()
    }

    fn parse_pow(&mut self) -> Result<f64, ParseError> {
        let left = self.parse_primary()?;
        self.skip_ws();
        if self.consume('^') {
            let right = self.parse_pow()?;
            let value = left.powf(right);
            Ok(value)
        } else {
            Ok(left)
        }
    }

    fn parse_primary(&mut self) -> Result<f64, ParseError> {
        self.skip_ws();
        if self.consume('(') {
            let value = self.parse_add_sub()?;
            self.skip_ws();
            if !self.consume(')') {
                return Err(ParseError("missing closing parenthesis"));
            }
            return Ok(value);
        }
        self.parse_number()
    }

    fn parse_number(&mut self) -> Result<f64, ParseError> {
        let start = self.pos;
        let mut seen_digit_before = false;

        if self.match_char('.') {
            if self.pos >= self.len || !self.expr[self.pos].is_ascii_digit() {
                return Err(ParseError("malformed number"));
            }
            while self.pos < self.len && self.expr[self.pos].is_ascii_digit() {
                self.pos += 1;
            }
        } else {
            while self.pos < self.len && self.expr[self.pos].is_ascii_digit() {
                self.pos += 1;
                seen_digit_before = true;
            }

            if self.match_char('.') {
                while self.pos < self.len && self.expr[self.pos].is_ascii_digit() {
                    self.pos += 1;
                }
            } else if !seen_digit_before {
                return Err(ParseError("malformed number"));
            }
        }

        if self.pos < self.len && (self.expr[self.pos] == 'e' || self.expr[self.pos] == 'E') {
            self.pos += 1;
            if self.pos < self.len && (self.expr[self.pos] == '+' || self.expr[self.pos] == '-') {
                self.pos += 1;
            }
            if self.pos >= self.len || !self.expr[self.pos].is_ascii_digit() {
                return Err(ParseError("malformed number"));
            }
            while self.pos < self.len && self.expr[self.pos].is_ascii_digit() {
                self.pos += 1;
            }
        }

        let token: String = self.expr[start..self.pos].iter().collect();
        let value = token.parse::<f64>().map_err(|_| ParseError("malformed number"))?;
        if !value.is_finite() {
            return Err(ParseError("non-finite number"));
        }
        Ok(value)
    }

    fn skip_ws(&mut self) {
        while self.pos < self.len && self.expr[self.pos].is_ascii_whitespace() {
            self.pos += 1;
        }
    }

    fn consume(&mut self, expected: char) -> bool {
        if self.pos < self.len && self.expr[self.pos] == expected {
            self.pos += 1;
            true
        } else {
            false
        }
    }

    fn match_char(&mut self, expected: char) -> bool {
        self.consume(expected)
    }
}

fn is_integer(v: f64) -> bool {
    v.fract() == 0.0
}

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() != 2 {
        eprintln!("error: expected one expression argument");
        std::process::exit(1);
    }

    let parser = Parser::new(&args[1]);
    match parser.parse() {
        Ok(value) => {
            if value.is_finite() {
                let output = if is_integer(value) {
                    format!("{:.0}", value)
                } else {
                    format!("{}", value)
                };
                println!("{}", output);
                std::process::exit(0);
            }
            eprintln!("error: non-finite result");
            std::process::exit(1);
        }
        Err(ParseError(msg)) => {
            eprintln!("error: {}", msg);
            std::process::exit(1);
        }
    }
}
