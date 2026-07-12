import Foundation

struct CalculatorError: Error {
    let message: String
}

final class Parser {
    private let input: [UInt8]
    private var position = 0

    init(_ source: String) {
        input = Array(source.utf8)
    }

    private func fail(_ message: String) throws -> Double {
        throw CalculatorError(message: message)
    }

    private func skipSpace() {
        while position < input.count && (input[position] == 32 || input[position] == 9 || input[position] == 10 || input[position] == 13 || input[position] == 11 || input[position] == 12) {
            position += 1
        }
    }

    private func parseNumber() throws -> Double {
        skipSpace()
        let start = position
        var before = 0
        while position < input.count && input[position] >= 48 && input[position] <= 57 {
            position += 1
            before += 1
        }
        var after = 0
        if position < input.count && input[position] == 46 {
            position += 1
            while position < input.count && input[position] >= 48 && input[position] <= 57 {
                position += 1
                after += 1
            }
        }
        if before + after == 0 { return try fail("expected number") }
        if position < input.count && (input[position] == 101 || input[position] == 69) {
            position += 1
            if position < input.count && (input[position] == 43 || input[position] == 45) { position += 1 }
            let exponentStart = position
            while position < input.count && input[position] >= 48 && input[position] <= 57 { position += 1 }
            if position == exponentStart { return try fail("invalid exponent") }
        }
        guard let value = Double(String(decoding: input[start..<position], as: UTF8.self)), value.isFinite else {
            return try fail("non-finite number")
        }
        return value
    }

    private func parsePrimary() throws -> Double {
        skipSpace()
        if position < input.count && input[position] == 40 {
            position += 1
            let value = try parseAdditive()
            skipSpace()
            if position >= input.count || input[position] != 41 { return try fail("expected ')'") }
            position += 1
            return value
        }
        return try parseNumber()
    }

    private func parsePower() throws -> Double {
        var value = try parsePrimary()
        skipSpace()
        if position < input.count && input[position] == 94 {
            position += 1
            value = pow(value, try parseUnary())
            if !value.isFinite { return try fail("non-finite result") }
        }
        return value
    }

    private func parseUnary() throws -> Double {
        skipSpace()
        if position < input.count && (input[position] == 43 || input[position] == 45) {
            let negative = input[position] == 45
            position += 1
            let value = try parseUnary()
            return negative ? -value : value
        }
        return try parsePower()
    }

    private func parseMultiplicative() throws -> Double {
        var value = try parseUnary()
        while true {
            skipSpace()
            if position >= input.count || (input[position] != 42 && input[position] != 47 && input[position] != 37) { return value }
            let operation = input[position]
            position += 1
            let right = try parseUnary()
            if right == 0 { return try fail("division by zero") }
            if operation == 42 { value *= right }
            else if operation == 47 { value /= right }
            else { value = value.truncatingRemainder(dividingBy: right) }
            if !value.isFinite { return try fail("non-finite result") }
        }
    }

    private func parseAdditive() throws -> Double {
        var value = try parseMultiplicative()
        while true {
            skipSpace()
            if position >= input.count || (input[position] != 43 && input[position] != 45) { return value }
            let operation = input[position]
            position += 1
            let right = try parseMultiplicative()
            value = operation == 43 ? value + right : value - right
            if !value.isFinite { return try fail("non-finite result") }
        }
    }

    func parse() throws -> Double {
        let value = try parseAdditive()
        skipSpace()
        if position != input.count { return try fail("unexpected token") }
        return value
    }
}

if CommandLine.arguments.count != 2 {
    fputs("error: expected exactly one expression\n", stderr)
    exit(1)
}

do {
    print(try Parser(CommandLine.arguments[1]).parse())
} catch let error as CalculatorError {
    fputs("error: \(error.message)\n", stderr)
    exit(1)
} catch {
    fputs("error: invalid expression\n", stderr)
    exit(1)
}
