use std::env;
use std::process;

type CalcResult<T> = Result<T, String>;

struct Parser {
    input: Vec<u8>,
    pos: usize,
}

impl Parser {
    fn new(text: &str) -> Self {
        Self { input: text.as_bytes().to_vec(), pos: 0 }
    }

    fn skip_space(&mut self) {
        while self.pos < self.input.len() && self.input[self.pos].is_ascii_whitespace() {
            self.pos += 1;
        }
    }

    fn take(&mut self, byte: u8) -> bool {
        self.skip_space();
        if self.pos < self.input.len() && self.input[self.pos] == byte {
            self.pos += 1;
            true
        } else {
            false
        }
    }

    fn parse(&mut self) -> CalcResult<f64> {
        let value = self.additive()?;
        self.skip_space();
        if self.pos != self.input.len() {
            return Err("unexpected token".into());
        }
        Ok(value)
    }

    fn additive(&mut self) -> CalcResult<f64> {
        let mut value = self.multiplicative()?;
        loop {
            if self.take(b'+') {
                value = checked(value + self.multiplicative()?)?;
            } else if self.take(b'-') {
                value = checked(value - self.multiplicative()?)?;
            } else {
                return Ok(value);
            }
        }
    }

    fn multiplicative(&mut self) -> CalcResult<f64> {
        let mut value = self.unary()?;
        loop {
            if self.take(b'*') {
                value = checked(value * self.unary()?)?;
            } else if self.take(b'/') {
                let divisor = self.unary()?;
                if divisor == 0.0 { return Err("division by zero".into()); }
                value = checked(value / divisor)?;
            } else if self.take(b'%') {
                let divisor = self.unary()?;
                if divisor == 0.0 { return Err("remainder by zero".into()); }
                value = checked(value % divisor)?;
            } else {
                return Ok(value);
            }
        }
    }

    fn unary(&mut self) -> CalcResult<f64> {
        if self.take(b'+') { return self.unary(); }
        if self.take(b'-') { return checked(-self.unary()?); }
        self.power()
    }

    fn power(&mut self) -> CalcResult<f64> {
        let mut value = self.primary()?;
        if self.take(b'^') {
            value = checked(value.powf(self.unary()?))?;
        }
        Ok(value)
    }

    fn primary(&mut self) -> CalcResult<f64> {
        if self.take(b'(') {
            let value = self.additive()?;
            if !self.take(b')') { return Err("expected closing parenthesis".into()); }
            return Ok(value);
        }
        self.number()
    }

    fn number(&mut self) -> CalcResult<f64> {
        self.skip_space();
        let start = self.pos;
        let mut before = 0;
        while self.pos < self.input.len() && self.input[self.pos].is_ascii_digit() {
            self.pos += 1; before += 1;
        }
        let mut after = 0;
        if self.pos < self.input.len() && self.input[self.pos] == b'.' {
            self.pos += 1;
            while self.pos < self.input.len() && self.input[self.pos].is_ascii_digit() {
                self.pos += 1; after += 1;
            }
        }
        if before == 0 && after == 0 { return Err("expected number".into()); }
        if self.pos < self.input.len() && matches!(self.input[self.pos], b'e' | b'E') {
            self.pos += 1;
            if self.pos < self.input.len() && matches!(self.input[self.pos], b'+' | b'-') { self.pos += 1; }
            let exponent_start = self.pos;
            while self.pos < self.input.len() && self.input[self.pos].is_ascii_digit() { self.pos += 1; }
            if self.pos == exponent_start { return Err("malformed exponent".into()); }
        }
        let token = std::str::from_utf8(&self.input[start..self.pos]).map_err(|_| "invalid number")?;
        checked(token.parse::<f64>().map_err(|_| "invalid number")?)
    }
}

fn checked(value: f64) -> CalcResult<f64> {
    if value.is_finite() { Ok(value) } else { Err("non-finite result".into()) }
}

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() != 2 {
        eprintln!("error: expected exactly one expression");
        process::exit(1);
    }
    match Parser::new(&args[1]).parse() {
        Ok(value) => println!("{}", value),
        Err(error) => { eprintln!("error: {}", error); process::exit(1); }
    }
}
