use std::env;

#[derive(Debug)]
struct CalcError(&'static str);

struct Parser<'a> {
    text: &'a [u8],
    pos: usize,
}

impl<'a> Parser<'a> {
    fn new(text: &'a str) -> Self { Self { text: text.as_bytes(), pos: 0 } }

    fn whitespace(&mut self) {
        while self.pos < self.text.len() && matches!(self.text[self.pos], b' ' | b'\t' | b'\n' | b'\r' | 0x0b | 0x0c) {
            self.pos += 1;
        }
    }

    fn number(&mut self) -> Result<f64, CalcError> {
        self.whitespace();
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
            self.pos = start;
            return Err(CalcError("expected number"));
        }
        if self.pos < self.text.len() && matches!(self.text[self.pos], b'e' | b'E') {
            self.pos += 1;
            if self.pos < self.text.len() && matches!(self.text[self.pos], b'+' | b'-') { self.pos += 1; }
            let exponent_start = self.pos;
            while self.pos < self.text.len() && self.text[self.pos].is_ascii_digit() { self.pos += 1; }
            if self.pos == exponent_start { return Err(CalcError("malformed exponent")); }
        }
        let raw = std::str::from_utf8(&self.text[start..self.pos]).map_err(|_| CalcError("invalid number"))?;
        let value: f64 = raw.parse().map_err(|_| CalcError("invalid number"))?;
        if !value.is_finite() { return Err(CalcError("non-finite number")); }
        Ok(value)
    }

    fn primary(&mut self) -> Result<f64, CalcError> {
        self.whitespace();
        if self.pos < self.text.len() && self.text[self.pos] == b'(' {
            self.pos += 1;
            let value = self.additive()?;
            self.whitespace();
            if self.pos >= self.text.len() || self.text[self.pos] != b')' { return Err(CalcError("expected closing parenthesis")); }
            self.pos += 1;
            Ok(value)
        } else { self.number() }
    }

    fn power(&mut self) -> Result<f64, CalcError> {
        let mut value = self.primary()?;
        self.whitespace();
        if self.pos < self.text.len() && self.text[self.pos] == b'^' {
            self.pos += 1;
            let exponent = self.unary()?;
            value = value.powf(exponent);
            if !value.is_finite() { return Err(CalcError("non-finite result")); }
        }
        Ok(value)
    }

    fn unary(&mut self) -> Result<f64, CalcError> {
        self.whitespace();
        if self.pos < self.text.len() && matches!(self.text[self.pos], b'+' | b'-') {
            let negative = self.text[self.pos] == b'-';
            self.pos += 1;
            let value = self.unary()?;
            Ok(if negative { -value } else { value })
        } else { self.power() }
    }

    fn multiplicative(&mut self) -> Result<f64, CalcError> {
        let mut value = self.unary()?;
        loop {
            self.whitespace();
            if self.pos >= self.text.len() || !matches!(self.text[self.pos], b'*' | b'/' | b'%') { return Ok(value); }
            let operator = self.text[self.pos];
            self.pos += 1;
            let right = self.unary()?;
            if right == 0.0 { return Err(CalcError("division by zero")); }
            value = match operator {
                b'*' => value * right,
                b'/' => value / right,
                _ => value % right,
            };
            if !value.is_finite() { return Err(CalcError("non-finite result")); }
        }
    }

    fn additive(&mut self) -> Result<f64, CalcError> {
        let mut value = self.multiplicative()?;
        loop {
            self.whitespace();
            if self.pos >= self.text.len() || !matches!(self.text[self.pos], b'+' | b'-') { return Ok(value); }
            let operator = self.text[self.pos];
            self.pos += 1;
            let right = self.multiplicative()?;
            value = if operator == b'+' { value + right } else { value - right };
            if !value.is_finite() { return Err(CalcError("non-finite result")); }
        }
    }

    fn parse(&mut self) -> Result<f64, CalcError> {
        self.whitespace();
        if self.pos == self.text.len() { return Err(CalcError("empty expression")); }
        let value = self.additive()?;
        self.whitespace();
        if self.pos != self.text.len() { return Err(CalcError("trailing tokens")); }
        Ok(value)
    }
}

fn main() {
    let args: Vec<String> = env::args().collect();
    let result = if args.len() != 2 {
        Err(CalcError("expected exactly one expression"))
    } else {
        Parser::new(&args[1]).parse()
    };
    match result {
        Ok(value) => println!("{:.17}", value),
        Err(CalcError(message)) => {
            eprintln!("error: {}", message);
            std::process::exit(1);
        }
    }
}
