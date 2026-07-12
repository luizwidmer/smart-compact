"use strict";

class CalculatorError extends Error {}

function checked(value) {
    if (!Number.isFinite(value)) {
        throw new CalculatorError("non-finite result");
    }
    return value;
}

class Parser {
    constructor(expression) {
        this.expression = expression;
        this.position = 0;
    }

    static isDigit(code) {
        return code >= 48 && code <= 57;
    }

    static isWhitespace(code) {
        return code === 32 || code === 9 || code === 13 || code === 10 || code === 11 || code === 12;
    }

    current() {
        return this.position < this.expression.length ? this.expression[this.position] : undefined;
    }

    skipWhitespace() {
        while (this.position < this.expression.length && Parser.isWhitespace(this.expression.charCodeAt(this.position))) {
            this.position += 1;
        }
    }

    parse() {
        const result = this.parseAddSub();
        this.skipWhitespace();
        if (this.position !== this.expression.length) {
            throw new CalculatorError("trailing tokens");
        }
        return checked(result);
    }

    parseAddSub() {
        let value = this.parseMulDiv();
        while (true) {
            this.skipWhitespace();
            const operation = this.current();
            if (operation !== "+" && operation !== "-") {
                return value;
            }
            this.position += 1;
            const right = this.parseMulDiv();
            value = checked(operation === "+" ? value + right : value - right);
        }
    }

    parseMulDiv() {
        let value = this.parseUnary();
        while (true) {
            this.skipWhitespace();
            const operation = this.current();
            if (operation !== "*" && operation !== "/" && operation !== "%") {
                return value;
            }
            this.position += 1;
            const right = this.parseUnary();
            if ((operation === "/" || operation === "%") && right === 0) {
                throw new CalculatorError("division or remainder by zero");
            }
            if (operation === "*") {
                value = checked(value * right);
            } else if (operation === "/") {
                value = checked(value / right);
            } else {
                value = checked(value % right);
            }
        }
    }

    parseUnary() {
        this.skipWhitespace();
        const operation = this.current();
        if (operation === "+" || operation === "-") {
            this.position += 1;
            const value = this.parseUnary();
            return checked(operation === "-" ? -value : value);
        }
        return this.parsePower();
    }

    parsePower() {
        const base = this.parsePrimary();
        this.skipWhitespace();
        if (this.current() !== "^") {
            return base;
        }
        this.position += 1;
        const exponent = this.parseUnary();
        return checked(Math.pow(base, exponent));
    }

    parsePrimary() {
        this.skipWhitespace();
        if (this.current() === "(") {
            this.position += 1;
            const value = this.parseAddSub();
            this.skipWhitespace();
            if (this.current() !== ")") {
                throw new CalculatorError("expected ')'" );
            }
            this.position += 1;
            return value;
        }
        return this.parseNumber();
    }

    parseNumber() {
        this.skipWhitespace();
        const start = this.position;

        while (Parser.isDigit(this.expression.charCodeAt(this.position))) {
            this.position += 1;
        }
        const digitsBefore = this.position > start;

        let digitsAfter = false;
        if (this.current() === ".") {
            this.position += 1;
            const fractionStart = this.position;
            while (Parser.isDigit(this.expression.charCodeAt(this.position))) {
                this.position += 1;
            }
            digitsAfter = this.position > fractionStart;
        }

        if (!digitsBefore && !digitsAfter) {
            throw new CalculatorError("expected number");
        }

        if (this.current() === "e" || this.current() === "E") {
            this.position += 1;
            if (this.current() === "+" || this.current() === "-") {
                this.position += 1;
            }
            const exponentStart = this.position;
            while (Parser.isDigit(this.expression.charCodeAt(this.position))) {
                this.position += 1;
            }
            if (this.position === exponentStart) {
                throw new CalculatorError("invalid exponent");
            }
        }

        const value = Number(this.expression.slice(start, this.position));
        return checked(value);
    }
}

try {
    const argumentsForExpression = process.argv.slice(2);
    if (argumentsForExpression.length !== 1) {
        throw new CalculatorError("expected exactly one expression argument");
    }
    const result = new Parser(argumentsForExpression[0]).parse();
    console.log(result.toPrecision(17));
} catch (error) {
    const message = error instanceof Error && error.message ? error.message : "calculation failed";
    console.error(`error: ${message}`);
    process.exitCode = 1;
}
