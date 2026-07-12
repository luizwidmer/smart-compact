"use strict";

class CalculatorError extends Error {}

function checked(value) {
    if (!Number.isFinite(value)) throw new CalculatorError("non-finite result");
    return value;
}

class Parser {
    constructor(expression) {
        this.expression = expression;
        this.position = 0;
    }

    current() { return this.position < this.expression.length ? this.expression[this.position] : undefined; }
    static isDigit(code) { return code >= 48 && code <= 57; }
    static isWhitespace(code) { return code === 32 || code === 9 || code === 10 || code === 11 || code === 12 || code === 13; }

    skipWhitespace() {
        while (this.position < this.expression.length && Parser.isWhitespace(this.expression.charCodeAt(this.position))) this.position++;
    }

    parse() {
        const result = this.parseAddSub();
        this.skipWhitespace();
        if (this.position !== this.expression.length) throw new CalculatorError("trailing tokens");
        return checked(result);
    }

    parseAddSub() {
        let value = this.parseMulDiv();
        while (true) {
            this.skipWhitespace();
            const operation = this.current();
            if (operation !== "+" && operation !== "-") return value;
            this.position++;
            const right = this.parseMulDiv();
            value = checked(operation === "+" ? value + right : value - right);
        }
    }

    parseMulDiv() {
        let value = this.parseUnary();
        while (true) {
            this.skipWhitespace();
            const operation = this.current();
            if (operation !== "*" && operation !== "/" && operation !== "%") return value;
            this.position++;
            const right = this.parseUnary();
            if ((operation === "/" || operation === "%") && right === 0) throw new CalculatorError("division or remainder by zero");
            value = checked(operation === "*" ? value * right : operation === "/" ? value / right : value % right);
        }
    }

    parseUnary() {
        this.skipWhitespace();
        const operation = this.current();
        if (operation === "+" || operation === "-") {
            this.position++;
            const value = this.parseUnary();
            return checked(operation === "-" ? -value : value);
        }
        return this.parsePower();
    }

    parsePower() {
        const base = this.parsePrimary();
        this.skipWhitespace();
        if (this.current() !== "^") return base;
        this.position++;
        return checked(Math.pow(base, this.parseUnary()));
    }

    parsePrimary() {
        this.skipWhitespace();
        if (this.current() === "(") {
            this.position++;
            const value = this.parseAddSub();
            this.skipWhitespace();
            if (this.current() !== ")") throw new CalculatorError("expected ')'");
            this.position++;
            return value;
        }
        return this.parseNumber();
    }

    parseNumber() {
        this.skipWhitespace();
        const start = this.position;
        while (Parser.isDigit(this.expression.charCodeAt(this.position))) this.position++;
        const digitsBefore = this.position > start;
        let digitsAfter = false;
        if (this.current() === ".") {
            this.position++;
            const fractionStart = this.position;
            while (Parser.isDigit(this.expression.charCodeAt(this.position))) this.position++;
            digitsAfter = this.position > fractionStart;
        }
        if (!digitsBefore && !digitsAfter) throw new CalculatorError("expected number");
        if (this.current() === "e" || this.current() === "E") {
            this.position++;
            if (this.current() === "+" || this.current() === "-") this.position++;
            const exponentStart = this.position;
            while (Parser.isDigit(this.expression.charCodeAt(this.position))) this.position++;
            if (this.position === exponentStart) throw new CalculatorError("invalid exponent");
        }
        return checked(Number(this.expression.slice(start, this.position)));
    }
}

function main() {
    if (process.argv.length !== 3) throw new CalculatorError("expected exactly one expression argument");
    console.log(new Parser(process.argv[2]).parse());
}

try { main(); }
catch (error) {
    console.error(`error: ${error instanceof CalculatorError ? error.message : "calculation failed"}`);
    process.exitCode = 1;
}
