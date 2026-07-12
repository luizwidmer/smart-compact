import Darwin
import Foundation

struct CalculatorError: Error {
    let message: String
}

struct Parser {
    private let input: [UInt8]
    private var position: Int = 0

    init(_ expression: String) {
        self.input = Array(expression.utf8)
    }

    private static func isDigit(_ byte: UInt8) -> Bool {
        byte >= 48 && byte <= 57
    }

    private static func isWhitespace(_ byte: UInt8) -> Bool {
        byte == 32 || byte == 9 || byte == 13 || byte == 10 || byte == 11 || byte == 12
    }

    private static func checked(_ value: Double) throws -> Double {
        guard value.isFinite else {
            throw CalculatorError(message: "non-finite result")
        }
        return value
    }

    private func current() -> UInt8? {
        guard position < input.count else { return nil }
        return input[position]
    }

    private mutating func skipWhitespace() {
        while let byte = current(), Self.isWhitespace(byte) {
            position += 1
        }
    }

    mutating func parse() throws -> Double {
        let result = try parseAddSub()
        skipWhitespace()
        guard position == input.count else {
            throw CalculatorError(message: "trailing tokens")
        }
        return try Self.checked(result)
    }

    private mutating func parseAddSub() throws -> Double {
        var value = try parseMulDiv()
        while true {
            skipWhitespace()
            guard let operation = current(), operation == 43 || operation == 45 else { break }
            position += 1
            let right = try parseMulDiv()
            value = try Self.checked(operation == 43 ? value + right : value - right)
        }
        return value
    }

    private mutating func parseMulDiv() throws -> Double {
        var value = try parseUnary()
        while true {
            skipWhitespace()
            guard let operation = current(), operation == 42 || operation == 47 || operation == 37 else { break }
            position += 1
            let right = try parseUnary()
            if (operation == 47 || operation == 37) && right == 0.0 {
                throw CalculatorError(message: "division or remainder by zero")
            }
            if operation == 42 {
                value = try Self.checked(value * right)
            } else if operation == 47 {
                value = try Self.checked(value / right)
            } else {
                value = try Self.checked(value.truncatingRemainder(dividingBy: right))
            }
        }
        return value
    }

    private mutating func parseUnary() throws -> Double {
        skipWhitespace()
        guard let operation = current(), operation == 43 || operation == 45 else {
            return try parsePower()
        }
        position += 1
        let value = try parseUnary()
        return try Self.checked(operation == 45 ? -value : value)
    }

    private mutating func parsePower() throws -> Double {
        let base = try parsePrimary()
        skipWhitespace()
        guard current() == 94 else { return base }
        position += 1
        let exponent = try parseUnary()
        return try Self.checked(Darwin.pow(base, exponent))
    }

    private mutating func parsePrimary() throws -> Double {
        skipWhitespace()
        if current() == 40 {
            position += 1
            let value = try parseAddSub()
            skipWhitespace()
            guard current() == 41 else {
                throw CalculatorError(message: "expected ')'")
            }
            position += 1
            return value
        }
        return try parseNumber()
    }

    private mutating func parseNumber() throws -> Double {
        skipWhitespace()
        let start = position

        while let byte = current(), Self.isDigit(byte) {
            position += 1
        }
        let digitsBefore = position > start

        var digitsAfter = false
        if current() == 46 {
            position += 1
            let fractionStart = position
            while let byte = current(), Self.isDigit(byte) {
                position += 1
            }
            digitsAfter = position > fractionStart
        }

        guard digitsBefore || digitsAfter else {
            throw CalculatorError(message: "expected number")
        }

        if current() == 101 || current() == 69 {
            position += 1
            if current() == 43 || current() == 45 {
                position += 1
            }
            let exponentStart = position
            while let byte = current(), Self.isDigit(byte) {
                position += 1
            }
            guard position > exponentStart else {
                throw CalculatorError(message: "invalid exponent")
            }
        }

        let token = String(decoding: input[start..<position], as: UTF8.self)
        guard let value = Double(token) else {
            throw CalculatorError(message: "invalid number")
        }
        return try Self.checked(value)
    }
}

func reportError(_ message: String) -> Never {
    let data = Data("error: \(message)\n".utf8)
    FileHandle.standardError.write(data)
    exit(1)
}

if CommandLine.arguments.count != 2 {
    reportError("expected exactly one expression argument")
}

do {
    var parser = Parser(CommandLine.arguments[1])
    let result = try parser.parse()
    print(result)
} catch let error as CalculatorError {
    reportError(error.message)
} catch {
    reportError("calculation failed")
}
