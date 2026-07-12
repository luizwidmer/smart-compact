"use strict";

class CalcError extends Error {}

function isDigit(character) {
    if (character === null) return false;
    const code = character.charCodeAt(0);
    return code >= 48 && code <= 57;
}

function isAsciiWhitespace(character) {
    if (character === null) return false;
    const code = character.charCodeAt(0);
    return (code >= 9 && code <= 13) || code === 32;
}

class Parser {
    constructor(text) {
        this.text = text;
        this.position = 0;
    }

    peek() {
        return this.position < this.text.length ? this.text[this.position] : null;
    }

    skipWhitespace() {
        while (isAsciiWhitespace(this.peek())) this.position += 1;
    }

    checked(value, message = "non-finite result") {
        if (!Number.isFinite(value)) throw new CalcError(message);
        return value;
    }

    parse() {
        const value = this.parseAdditive();
        this.skipWhitespace();
        if (this.position !== this.text.length) throw new CalcError("unexpected trailing token");
        return this.checked(value);
    }

    parseAdditive() {
        let value = this.parseMultiplicative();
        while (true) {
            this.skipWhitespace();
            const operator = this.peek();
            if (operator !== "+" && operator !== "-") return value;
            this.position += 1;
            const right = this.parseMultiplicative();
            value = operator === "+" ? value + right : value - right;
            value = this.checked(value);
        }
    }

    parseMultiplicative() {
        let value = this.parseUnary();
        while (true) {
            this.skipWhitespace();
            const operator = this.peek();
            if (operator !== "*" && operator !== "/" && operator !== "%") return value;
            this.position += 1;
            const right = this.parseUnary();
            if (operator === "/") {
                if (right === 0) throw new CalcError("division by zero");
                value /= right;
            } else if (operator === "%") {
                if (right === 0) throw new CalcError("remainder by zero");
                value %= right;
            } else {
                value *= right;
            }
            value = this.checked(value);
        }
    }

    parseUnary() {
        this.skipWhitespace();
        const operator = this.peek();
        if (operator !== "+" && operator !== "-") return this.parsePower();
        this.position += 1;
        let value = this.parseUnary();
        if (operator === "-") value = -value;
        return this.checked(value);
    }

    parsePower() {
        const left = this.parsePrimary();
        this.skipWhitespace();
        if (this.peek() !== "^") return left;
        this.position += 1;
        const right = this.parseUnary();
        return this.checked(Math.pow(left, right));
    }

    parsePrimary() {
        this.skipWhitespace();
        if (this.peek() === "(") {
            this.position += 1;
            const value = this.parseAdditive();
            this.skipWhitespace();
            if (this.peek() !== ")") throw new CalcError("expected ')'");
            this.position += 1;
            return value;
        }
        if (isDigit(this.peek()) || this.peek() === ".") return this.parseNumber();
        throw new CalcError("expected number or '('");
    }

    parseNumber() {
        const start = this.position;
        let digits = 0;
        while (isDigit(this.peek())) {
            this.position += 1;
            digits += 1;
        }
        if (this.peek() === ".") {
            this.position += 1;
            while (isDigit(this.peek())) {
                this.position += 1;
                digits += 1;
            }
        }
        if (digits === 0) throw new CalcError("expected digits");
        if (this.peek() === "e" || this.peek() === "E") {
            this.position += 1;
            if (this.peek() === "+" || this.peek() === "-") this.position += 1;
            const exponentStart = this.position;
            while (isDigit(this.peek())) this.position += 1;
            if (this.position === exponentStart) throw new CalcError("expected exponent digits");
        }
        const value = Number(this.text.slice(start, this.position));
        return this.checked(value, "non-finite input");
    }
}

function fail(message) {
    console.error(`error: ${message}`);
    process.exit(1);
}

const argumentsList = process.argv.slice(2);
if (argumentsList.length !== 1) fail("expected exactly one expression argument");

try {
    const result = new Parser(argumentsList[0]).parse();
    console.log(Object.is(result, -0) ? "-0" : String(result));
} catch (error) {
    if (error instanceof CalcError) fail(error.message);
    fail("invalid expression");
}
