#if canImport(Darwin)
import Darwin
#else
import Glibc
#endif
import Foundation

enum ParseError: Error {
    case invalid
}

struct Parser {
    let input: [UInt8]
    var position: Int = 0

    init(_ text: String) {
        input = Array(text.utf8)
    }

    func peek() -> UInt8? {
        guard position < input.count else { return nil }
        return input[position]
    }

    func isDigit(_ byte: UInt8) -> Bool {
        byte >= 48 && byte <= 57
    }

    mutating func skipWhitespace() {
        while let byte = peek(), byte == 32 || byte == 9 || byte == 10 || byte == 11 || byte == 12 || byte == 13 {
            position += 1
        }
    }

    func checked(_ value: Double) throws -> Double {
        guard value.isFinite else { throw ParseError.invalid }
        return value
    }

    mutating func parse() throws -> Double {
        let value = try parseAdditive()
        skipWhitespace()
        guard position == input.count else { throw ParseError.invalid }
        return value
    }

    mutating func parseAdditive() throws -> Double {
        var left = try parseMultiplicative()
        while true {
            skipWhitespace()
            guard let op = peek(), op == 43 || op == 45 else { return left }
            position += 1
            let right = try parseMultiplicative()
            left = try checked(op == 43 ? left + right : left - right)
        }
    }

    mutating func parseMultiplicative() throws -> Double {
        var left = try parseUnary()
        while true {
            skipWhitespace()
            guard let op = peek(), op == 42 || op == 47 || op == 37 else { return left }
            position += 1
            let right = try parseUnary()
            if (op == 47 || op == 37) && right == 0.0 {
                throw ParseError.invalid
            }
            let value: Double
            if op == 42 {
                value = left * right
            } else if op == 47 {
                value = left / right
            } else {
                value = left.truncatingRemainder(dividingBy: right)
            }
            left = try checked(value)
        }
    }

    mutating func parseUnary() throws -> Double {
        skipWhitespace()
        if peek() == 43 {
            position += 1
            return try parseUnary()
        }
        if peek() == 45 {
            position += 1
            let value = try parseUnary()
            return try checked(-value)
        }
        return try parsePower()
    }

    mutating func parsePower() throws -> Double {
        let base = try parsePrimary()
        skipWhitespace()
        guard peek() == 94 else { return base }
        position += 1
        let exponent = try parseUnary()
        return try checked(pow(base, exponent))
    }

    mutating func parsePrimary() throws -> Double {
        skipWhitespace()
        if peek() == 40 {
            position += 1
            let value = try parseAdditive()
            skipWhitespace()
            guard peek() == 41 else { throw ParseError.invalid }
            position += 1
            return value
        }
        return try parseNumber()
    }

    mutating func parseNumber() throws -> Double {
        skipWhitespace()
        let start = position
        var hasDigit = false
        while let byte = peek(), isDigit(byte) {
            position += 1
            hasDigit = true
        }
        if peek() == 46 {
            position += 1
            while let byte = peek(), isDigit(byte) {
                position += 1
                hasDigit = true
            }
        }
        guard hasDigit else { throw ParseError.invalid }
        if let byte = peek(), byte == 101 || byte == 69 {
            position += 1
            if let sign = peek(), sign == 43 || sign == 45 {
                position += 1
            }
            let exponentStart = position
            while let digit = peek(), isDigit(digit) {
                position += 1
            }
            guard position != exponentStart else { throw ParseError.invalid }
        }
        let literal = String(decoding: input[start..<position], as: UTF8.self)
        guard let value = Double(literal) else { throw ParseError.invalid }
        return try checked(value)
    }
}

func reportError() -> Never {
    FileHandle.standardError.write(Data("error: invalid expression\n".utf8))
    exit(1)
}

let arguments = CommandLine.arguments
if arguments.count != 2 {
    reportError()
}

do {
    var parser = Parser(arguments[1])
    let result = try parser.parse()
    print(result)
} catch {
    reportError()
}
