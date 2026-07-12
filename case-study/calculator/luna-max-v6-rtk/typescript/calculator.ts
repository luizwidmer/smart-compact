"use strict";

class ParseError extends Error {}

class Parser {
    input: string;
    position: number;

    constructor(input: string) {
        this.input = input;
        this.position = 0;
    }

    fail(): never {
        throw new ParseError();
    }

    peek(): number {
        return this.position < this.input.length ? this.input.charCodeAt(this.position) : -1;
    }

    isDigit(code: number): boolean {
        return code >= 48 && code <= 57;
    }

    skipWhitespace(): void {
        while (this.peek() === 32 || (this.peek() >= 9 && this.peek() <= 13)) {
            this.position += 1;
        }
    }

    checked(value: number): number {
        if (!Number.isFinite(value)) {
            this.fail();
        }
        return value;
    }

    parse(): number {
        const value = this.parseAdditive();
        this.skipWhitespace();
        if (this.position !== this.input.length) {
            this.fail();
        }
        return value;
    }

    parseAdditive(): number {
        let left = this.parseMultiplicative();
        while (true) {
            this.skipWhitespace();
            const operator = this.peek();
            if (operator !== 43 && operator !== 45) {
                return left;
            }
            this.position += 1;
            const right = this.parseMultiplicative();
            left = this.checked(operator === 43 ? left + right : left - right);
        }
    }

    parseMultiplicative(): number {
        let left = this.parseUnary();
        while (true) {
            this.skipWhitespace();
            const operator = this.peek();
            if (operator !== 42 && operator !== 47 && operator !== 37) {
                return left;
            }
            this.position += 1;
            const right = this.parseUnary();
            if ((operator === 47 || operator === 37) && right === 0) {
                this.fail();
            }
            const value = operator === 42 ? left * right : operator === 47 ? left / right : left % right;
            left = this.checked(value);
        }
    }

    parseUnary(): number {
        this.skipWhitespace();
        if (this.peek() === 43) {
            this.position += 1;
            return this.parseUnary();
        }
        if (this.peek() === 45) {
            this.position += 1;
            return this.checked(-this.parseUnary());
        }
        return this.parsePower();
    }

    parsePower(): number {
        const base = this.parsePrimary();
        this.skipWhitespace();
        if (this.peek() !== 94) {
            return base;
        }
        this.position += 1;
        const exponent = this.parseUnary();
        return this.checked(Math.pow(base, exponent));
    }

    parsePrimary(): number {
        this.skipWhitespace();
        if (this.peek() === 40) {
            this.position += 1;
            const value = this.parseAdditive();
            this.skipWhitespace();
            if (this.peek() !== 41) {
                this.fail();
            }
            this.position += 1;
            return value;
        }
        return this.parseNumber();
    }

    parseNumber(): number {
        this.skipWhitespace();
        const start = this.position;
        let hasDigit = false;
        while (this.isDigit(this.peek())) {
            this.position += 1;
            hasDigit = true;
        }
        if (this.peek() === 46) {
            this.position += 1;
            while (this.isDigit(this.peek())) {
                this.position += 1;
                hasDigit = true;
            }
        }
        if (!hasDigit) {
            this.fail();
        }
        if (this.peek() === 101 || this.peek() === 69) {
            this.position += 1;
            if (this.peek() === 43 || this.peek() === 45) {
                this.position += 1;
            }
            const exponentStart = this.position;
            while (this.isDigit(this.peek())) {
                this.position += 1;
            }
            if (this.position === exponentStart) {
                this.fail();
            }
        }
        return this.checked(Number(this.input.slice(start, this.position)));
    }
}

function main(): void {
    if (process.argv.length !== 3) {
        console.error("error: invalid expression");
        process.exitCode = 1;
        return;
    }
    try {
        const result = new Parser(process.argv[2]).parse();
        console.log(String(result));
    } catch (error) {
        console.error("error: invalid expression");
        process.exitCode = 1;
    }
}

main();
