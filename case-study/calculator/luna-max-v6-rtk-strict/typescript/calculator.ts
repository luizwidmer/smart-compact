"use strict";

class ParseError extends Error {}

class Parser {
    input: string;
    position: number;

    constructor(input: string) {
        this.input = input;
        this.position = 0;
    }

    parse(): number {
        const value = this.parseAdditive();
        this.skipWhitespace();
        if (this.position !== this.input.length) {
            throw new ParseError("trailing tokens");
        }
        return this.checked(value);
    }

    skipWhitespace(): void {
        while (this.position < this.input.length && " \t\n\r\f\v".includes(this.input[this.position])) {
            this.position += 1;
        }
    }

    peek(): string | null {
        this.skipWhitespace();
        return this.position === this.input.length ? null : this.input[this.position];
    }

    checked(value: number): number {
        if (!Number.isFinite(value)) {
            throw new ParseError("non-finite result");
        }
        return value;
    }

    parseAdditive(): number {
        let left = this.parseMultiplicative();
        while (true) {
            const operation = this.peek();
            if (operation !== "+" && operation !== "-") {
                return left;
            }
            this.position += 1;
            const right = this.parseMultiplicative();
            left = this.checked(operation === "+" ? left + right : left - right);
        }
    }

    parseMultiplicative(): number {
        let left = this.parseUnary();
        while (true) {
            const operation = this.peek();
            if (operation !== "*" && operation !== "/" && operation !== "%") {
                return left;
            }
            this.position += 1;
            const right = this.parseUnary();
            if ((operation === "/" || operation === "%") && right === 0) {
                throw new ParseError("division or remainder by zero");
            }
            let result: number;
            if (operation === "*") {
                result = left * right;
            } else if (operation === "/") {
                result = left / right;
            } else {
                result = left % right;
            }
            left = this.checked(result);
        }
    }

    parseUnary(): number {
        const operation = this.peek();
        if (operation === "+" || operation === "-") {
            this.position += 1;
            const value = this.parseUnary();
            return this.checked(operation === "+" ? value : -value);
        }
        return this.parsePower();
    }

    parsePower(): number {
        const base = this.parsePrimary();
        if (this.peek() === "^") {
            this.position += 1;
            const exponent = this.parseUnary();
            return this.checked(Math.pow(base, exponent));
        }
        return base;
    }

    parsePrimary(): number {
        if (this.peek() === "(") {
            this.position += 1;
            const value = this.parseAdditive();
            if (this.peek() !== ")") {
                throw new ParseError("missing closing parenthesis");
            }
            this.position += 1;
            return value;
        }
        return this.parseNumber();
    }

    isDigit(character: string | null): boolean {
        return character !== null && character >= "0" && character <= "9";
    }

    parseNumber(): number {
        this.skipWhitespace();
        const start = this.position;
        let digitsBefore = 0;
        while (this.isDigit(this.input[this.position] ?? null)) {
            this.position += 1;
            digitsBefore += 1;
        }

        let digitsAfter = 0;
        if (this.input[this.position] === ".") {
            this.position += 1;
            while (this.isDigit(this.input[this.position] ?? null)) {
                this.position += 1;
                digitsAfter += 1;
            }
        }

        if (digitsBefore === 0 && digitsAfter === 0) {
            throw new ParseError("expected number or parenthesis");
        }

        if (this.input[this.position] === "e" || this.input[this.position] === "E") {
            this.position += 1;
            if (this.input[this.position] === "+" || this.input[this.position] === "-") {
                this.position += 1;
            }
            const exponentStart = this.position;
            while (this.isDigit(this.input[this.position] ?? null)) {
                this.position += 1;
            }
            if (this.position === exponentStart) {
                throw new ParseError("malformed exponent");
            }
        }

        return this.checked(Number(this.input.slice(start, this.position)));
    }
}

function main(): void {
    if (process.argv.length !== 3) {
        throw new ParseError("expected exactly one expression argument");
    }
    const result = new Parser(process.argv[2]).parse();
    const output = Object.is(result, -0) ? "-0" : result.toString();
    process.stdout.write(output + "\n");
}

try {
    main();
} catch (error) {
    const message = error instanceof Error ? error.message : "calculation failed";
    process.stderr.write("error: " + message + "\n");
    process.exitCode = 1;
}
