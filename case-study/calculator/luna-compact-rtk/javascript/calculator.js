"use strict";

class CalculatorError extends Error {}

class Parser {
    constructor(expression) {
        this.expression = expression;
        this.position = 0;
    }

    parse() {
        const value = this.parseAddition();
        this.skipWhitespace();
        if (this.position !== this.expression.length) {
            throw new CalculatorError("unexpected trailing token");
        }
        return value;
    }

    parseAddition() {
        let value = this.parseMultiplication();
        while (true) {
            if (this.consume("+")) {
                value = this.checked(value + this.parseMultiplication());
            } else if (this.consume("-")) {
                value = this.checked(value - this.parseMultiplication());
            } else {
                return value;
            }
        }
    }

    parseMultiplication() {
        let value = this.parseUnary();
        while (true) {
            if (this.consume("*")) {
                value = this.checked(value * this.parseUnary());
            } else if (this.consume("/")) {
                const right = this.parseUnary();
                if (right === 0) {
                    throw new CalculatorError("division by zero");
                }
                value = this.checked(value / right);
            } else if (this.consume("%")) {
                const right = this.parseUnary();
                if (right === 0) {
                    throw new CalculatorError("remainder by zero");
                }
                value = this.checked(value % right);
            } else {
                return value;
            }
        }
    }

    parseUnary() {
        if (this.consume("+")) {
            return this.parseUnary();
        }
        if (this.consume("-")) {
            return -this.parseUnary();
        }
        return this.parsePower();
    }

    parsePower() {
        const value = this.parsePrimary();
        if (this.consume("^")) {
            const exponent = this.parseUnary();
            return this.checked(Math.pow(value, exponent));
        }
        return value;
    }

    parsePrimary() {
        this.skipWhitespace();
        if (this.position >= this.expression.length) {
            throw new CalculatorError("expected a number or parenthesized expression");
        }

        const character = this.expression[this.position];
        if (character === "(") {
            this.position += 1;
            const value = this.parseAddition();
            if (!this.consume(")")) {
                throw new CalculatorError("missing closing parenthesis");
            }
            return value;
        }

        if (this.isDigit(character) || character === ".") {
            return this.parseNumber();
        }
        throw new CalculatorError("expected a number or parenthesized expression");
    }

    parseNumber() {
        const start = this.position;
        let digitsBeforeDecimal = 0;
        while (this.position < this.expression.length &&
               this.isDigit(this.expression[this.position])) {
            this.position += 1;
            digitsBeforeDecimal += 1;
        }

        let digitsAfterDecimal = 0;
        if (this.expression[this.position] === ".") {
            this.position += 1;
            while (this.position < this.expression.length &&
                   this.isDigit(this.expression[this.position])) {
                this.position += 1;
                digitsAfterDecimal += 1;
            }
        }

        if (digitsBeforeDecimal === 0 && digitsAfterDecimal === 0) {
            throw new CalculatorError("invalid number");
        }

        if (this.expression[this.position] === "e" || this.expression[this.position] === "E") {
            this.position += 1;
            if (this.expression[this.position] === "+" || this.expression[this.position] === "-") {
                this.position += 1;
            }
            let exponentDigits = 0;
            while (this.position < this.expression.length &&
                   this.isDigit(this.expression[this.position])) {
                this.position += 1;
                exponentDigits += 1;
            }
            if (exponentDigits === 0) {
                throw new CalculatorError("invalid exponent");
            }
        }

        const literal = this.expression.slice(start, this.position);
        return this.checked(Number(literal));
    }

    consume(token) {
        this.skipWhitespace();
        if (this.expression.startsWith(token, this.position)) {
            this.position += token.length;
            return true;
        }
        return false;
    }

    skipWhitespace() {
        while (this.position < this.expression.length &&
               this.isWhitespace(this.expression.charCodeAt(this.position))) {
            this.position += 1;
        }
    }

    isDigit(character) {
        return character !== undefined && character >= "0" && character <= "9";
    }

    isWhitespace(code) {
        return code === 32 || code === 9 || code === 10 || code === 13 || code === 11 || code === 12;
    }

    checked(value) {
        if (!Number.isFinite(value)) {
            throw new CalculatorError("non-finite result");
        }
        return value;
    }
}

function main() {
    if (process.argv.length !== 3) {
        throw new CalculatorError("expected exactly one expression argument");
    }
    return new Parser(process.argv[2]).parse();
}

try {
    console.log(String(main()));
} catch (error) {
    const message = error instanceof CalculatorError ? error.message : "invalid expression";
    console.error(`error: ${message}`);
    process.exitCode = 1;
}
