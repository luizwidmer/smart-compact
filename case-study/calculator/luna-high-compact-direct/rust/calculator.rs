use std::env;
use std::process;

struct Parser<'a> {
    input: &'a [u8],
    pos: usize,
}

impl<'a> Parser<'a> {
    fn new(text: &'a str) -> Self {
        Self { input: text.as_bytes(), pos: 0 }
    }

    fn skip_space(&mut self) {
        while self.pos < self.input.len() && b" \t\n\r\x0b\x0c".contains(&self.input[self.pos]) {
            self.pos += 1;
        }
    }

    fn take(&mut self, token: u8) -> bool {
        self.skip_space();
        if self.pos < self.input.len() && self.input[self.pos] == token {
            self.pos += 1;
            true
        } else {
            false
        }
    }

    fn expression(&mut self) -> Result<f64, ()> {
        let mut value = self.term()?;
        loop {
            if self.take(b'+') {
                let right = self.term()?;
                value = self.checked(value + right)?;
            } else if self.take(b'-') {
                let right = self.term()?;
                value = self.checked(value - right)?;
            } else {
                return Ok(value);
            }
        }
    }

    fn term(&mut self) -> Result<f64, ()> {
        let mut value = self.unary()?;
        loop {
            if self.take(b'*') {
                let right = self.unary()?;
                value = self.checked(value * right)?;
            } else if self.take(b'/') {
                let right = self.unary()?;
                if right == 0.0 { return Err(()); }
                value = self.checked(value / right)?;
            } else if self.take(b'%') {
                let right = self.unary()?;
                if right == 0.0 { return Err(()); }
                value = self.checked(value % right)?;
            } else {
                return Ok(value);
            }
        }
    }

    fn unary(&mut self) -> Result<f64, ()> {
        if self.take(b'+') { return self.unary(); }
        if self.take(b'-') {
            let value = self.unary()?;
            return self.checked(-value);
        }
        self.power()
    }

    fn power(&mut self) -> Result<f64, ()> {
        let value = self.primary()?;
        if self.take(b'^') {
            let exponent = self.unary()?;
            return self.checked(value.powf(exponent));
        }
        Ok(value)
    }

    fn primary(&mut self) -> Result<f64, ()> {
        if self.take(b'(') {
            let value = self.expression()?;
            if !self.take(b')') { return Err(()); }
            return Ok(value);
        }

        self.skip_space();
        let start = self.pos;
        while self.pos < self.input.len() && self.input[self.pos].is_ascii_digit() { self.pos += 1; }
        if self.pos < self.input.len() && self.input[self.pos] == b'.' {
            self.pos += 1;
            while self.pos < self.input.len() && self.input[self.pos].is_ascii_digit() { self.pos += 1; }
        }
        if self.pos == start && self.pos < self.input.len() && self.input[self.pos] == b'.' {
            self.pos += 1;
            let fraction_start = self.pos;
            while self.pos < self.input.len() && self.input[self.pos].is_ascii_digit() { self.pos += 1; }
            if self.pos == fraction_start { return Err(()); }
        }
        if self.pos == start { return Err(()); }
        if self.pos < self.input.len() && (self.input[self.pos] == b'e' || self.input[self.pos] == b'E') {
            self.pos += 1;
            if self.pos < self.input.len() && (self.input[self.pos] == b'+' || self.input[self.pos] == b'-') { self.pos += 1; }
            let exponent_start = self.pos;
            while self.pos < self.input.len() && self.input[self.pos].is_ascii_digit() { self.pos += 1; }
            if self.pos == exponent_start { return Err(()); }
        }
        let text = std::str::from_utf8(&self.input[start..self.pos]).map_err(|_| ())?;
        self.checked(text.parse::<f64>().map_err(|_| ())?)
    }

    fn checked(&self, value: f64) -> Result<f64, ()> {
        if value.is_finite() { Ok(value) } else { Err(()) }
    }

    fn parse(&mut self) -> Result<f64, ()> {
        let value = self.expression()?;
        self.skip_space();
        if self.pos != self.input.len() { return Err(()); }
        self.checked(value)
    }
}

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() != 2 {
        eprintln!("error: expected exactly one expression argument");
        process::exit(2);
    }
    match Parser::new(&args[1]).parse() {
        Ok(value) => println!("{:.17}", value),
        Err(()) => {
            eprintln!("error: invalid expression");
            process::exit(1);
        }
    }
}
