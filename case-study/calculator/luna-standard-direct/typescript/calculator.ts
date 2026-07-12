"use strict";

class CalcError extends Error {}

function isDigit(character: string | null): boolean {
    if (character === null) return false;
    const code = character.charCodeAt(0);
    return code >= 48 && code <= 57;
}

function isAsciiWhitespace(character: string | null): boolean {
    if (character === null) return false;
    const code = character.charCodeAt(0);
    return (code >= 9 && code <= 13) || code === 32;
}

class Parser {
    private readonly text: string;
    private position: number = 0;

    constructor(text: string) {
        this.text = text;
    }

    private peek(): string | null {
        return this.position < this.text.length ? this.text[this.position] : null;
    }

    private skipWhitespace(): void {
        while (isAsciiWhitespace(this.peek())) this.position += 1;
    }

    private checked(value: number, message: string = "non-finite result"): number {
        if (!Number.isFinite(value)) throw new CalcError(message);
        return value;
    }

    parse(): number {
        const value = this.parseAdditive();
        this.skipWhitespace();
        if (this.position !== this.text.length) throw new CalcError("unexpected trailing token");
        return this.checked(value);
    }

    private parseAdditive(): number {
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

    private parseMultiplicative(): number {
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

    private parseUnary(): number {
        this.skipWhitespace();
        const operator = this.peek();
        if (operator !== "+" && operator !== "-") return this.parsePower();
        this.position += 1;
        let value = this.parseUnary();
        if (operator === "-") value = -value;
        return this.checked(value);
    }

    private parsePower(): number {
        const left = this.parsePrimary();
        this.skipWhitespace();
        if (this.peek() !== "^") return left;
        this.position += 1;
        const right = this.parseUnary();
        return this.checked(Math.pow(left, right));
    }

    private parsePrimary(): number {
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

    private parseNumber(): number {
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

function fail(message: string): never {
    console.error(`error: ${message}`);
    process.exit(1);
}

const argumentsList: string[] = process.argv.slice(2);
if (argumentsList.length !== 1) fail("expected exactly one expression argument");

try {
    const result = new Parser(argumentsList[0]).parse();
    console.log(Object.is(result, -0) ? "-0" : String(result));
} catch (error) {
    if (error instanceof CalcError) fail(error.message);
    fail("invalid expression");
}
