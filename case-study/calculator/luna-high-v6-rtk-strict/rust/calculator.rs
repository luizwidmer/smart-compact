use std::env;

struct Parser<'a> {
    text: &'a [u8],
    pos: usize,
}

impl<'a> Parser<'a> {
    fn new(text: &'a str) -> Self {
        Self { text: text.as_bytes(), pos: 0 }
    }

    fn is_space(byte: u8) -> bool {
        matches!(byte, b' ' | b'\t' | b'\n' | b'\r' | b'\x0b' | b'\x0c')
    }

    fn skip_space(&mut self) {
        while self.pos < self.text.len() && Self::is_space(self.text[self.pos]) {
            self.pos += 1;
        }
    }

    fn checked(value: f64) -> Result<f64, String> {
        if value.is_finite() { Ok(value) } else { Err("non-finite result".into()) }
    }

    fn parse(&mut self) -> Result<f64, String> {
        let value = self.parse_additive()?;
        self.skip_space();
        if self.pos != self.text.len() { return Err("trailing tokens".into()); }
        Self::checked(value)
    }

    fn parse_additive(&mut self) -> Result<f64, String> {
        let mut value = self.parse_multiplicative()?;
        loop {
            self.skip_space();
            if self.pos >= self.text.len() || !matches!(self.text[self.pos], b'+' | b'-') { return Ok(value); }
            let operator = self.text[self.pos];
            self.pos += 1;
            let right = self.parse_multiplicative()?;
            value = Self::checked(if operator == b'+' { value + right } else { value - right })?;
        }
    }

    fn parse_multiplicative(&mut self) -> Result<f64, String> {
        let mut value = self.parse_unary()?;
        loop {
            self.skip_space();
            if self.pos >= self.text.len() || !matches!(self.text[self.pos], b'*' | b'/' | b'%') { return Ok(value); }
            let operator = self.text[self.pos];
            self.pos += 1;
            let right = self.parse_unary()?;
            if right == 0.0 { return Err("division by zero".into()); }
            value = Self::checked(match operator {
                b'*' => value * right,
                b'/' => value / right,
                _ => value % right,
            })?;
        }
    }

    fn parse_unary(&mut self) -> Result<f64, String> {
        self.skip_space();
        if self.pos < self.text.len() && matches!(self.text[self.pos], b'+' | b'-') {
            let operator = self.text[self.pos];
            self.pos += 1;
            let value = self.parse_unary()?;
            return Self::checked(if operator == b'+' { value } else { -value });
        }
        self.parse_power()
    }

    fn parse_power(&mut self) -> Result<f64, String> {
        let value = self.parse_primary()?;
        self.skip_space();
        if self.pos < self.text.len() && self.text[self.pos] == b'^' {
            self.pos += 1;
            return Self::checked(value.powf(self.parse_unary()?));
        }
        Ok(value)
    }

    fn parse_primary(&mut self) -> Result<f64, String> {
        self.skip_space();
        if self.pos >= self.text.len() { return Err("expected expression".into()); }
        if self.text[self.pos] == b'(' {
            self.pos += 1;
            let value = self.parse_additive()?;
            self.skip_space();
            if self.pos >= self.text.len() || self.text[self.pos] != b')' { return Err("expected closing parenthesis".into()); }
            self.pos += 1;
            return Ok(value);
        }
        self.parse_number()
    }

    fn parse_number(&mut self) -> Result<f64, String> {
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
        if digits == 0 { return Err("expected number".into()); }
        if self.pos < self.text.len() && matches!(self.text[self.pos], b'e' | b'E') {
            self.pos += 1;
            if self.pos < self.text.len() && matches!(self.text[self.pos], b'+' | b'-') { self.pos += 1; }
            let exponent_start = self.pos;
            while self.pos < self.text.len() && self.text[self.pos].is_ascii_digit() { self.pos += 1; }
            if self.pos == exponent_start { return Err("invalid exponent".into()); }
        }
        let token = std::str::from_utf8(&self.text[start..self.pos]).map_err(|_| "invalid number")?;
        let value = token.parse::<f64>().map_err(|_| "invalid number")?;
        Self::checked(value)
    }
}

fn main() {
    let args: Vec<String> = env::args().collect();
    let result = if args.len() != 2 {
        Err("expected exactly one argument".to_string())
    } else {
        Parser::new(&args[1]).parse()
    };
    match result {
        Ok(value) => println!("{:.17}", value),
        Err(message) => {
            eprintln!("error: {}", message);
            std::process::exit(1);
        }
    }
}
