"use strict";

class CalculatorError extends Error {}

function checked(value: number): number {
    if (!Number.isFinite(value)) throw new CalculatorError("non-finite result");
    return value;
}

class Parser {
    private position = 0;
    private readonly expression: string;
    constructor(expression: string) { this.expression = expression; }

    private current(): string | undefined { return this.position < this.expression.length ? this.expression[this.position] : undefined; }
    private static isDigit(code: number): boolean { return code >= 48 && code <= 57; }
    private static isWhitespace(code: number): boolean { return code === 32 || code === 9 || code === 10 || code === 11 || code === 12 || code === 13; }
    private skipWhitespace(): void {
        while (this.position < this.expression.length && Parser.isWhitespace(this.expression.charCodeAt(this.position))) this.position++;
    }

    parse(): number {
        const result = this.parseAddSub();
        this.skipWhitespace();
        if (this.position !== this.expression.length) throw new CalculatorError("trailing tokens");
        return checked(result);
    }

    private parseAddSub(): number {
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

    private parseMulDiv(): number {
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

    private parseUnary(): number {
        this.skipWhitespace();
        const operation = this.current();
        if (operation === "+" || operation === "-") {
            this.position++;
            const value = this.parseUnary();
            return checked(operation === "-" ? -value : value);
        }
        return this.parsePower();
    }

    private parsePower(): number {
        const base = this.parsePrimary();
        this.skipWhitespace();
        if (this.current() !== "^") return base;
        this.position++;
        return checked(Math.pow(base, this.parseUnary()));
    }

    private parsePrimary(): number {
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

    private parseNumber(): number {
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

try {
    if (process.argv.length !== 3) throw new CalculatorError("expected exactly one expression argument");
    const result = new Parser(process.argv[2]).parse();
    console.log(result);
} catch (error) {
    console.error(`error: ${error instanceof CalculatorError ? error.message : "calculation failed"}`);
    process.exitCode = 1;
}
