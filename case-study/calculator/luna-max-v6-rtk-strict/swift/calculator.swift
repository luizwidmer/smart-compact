import Foundation

#if canImport(Darwin)
import Darwin
#elseif canImport(Glibc)
import Glibc
#endif

struct ParseError: Error {
    let message: String
}

struct Parser {
    let input: [UInt8]
    var position: Int = 0

    init(_ text: String) {
        self.input = Array(text.utf8)
    }

    mutating func parse() throws -> Double {
        let value = try parseAdditive()
        skipWhitespace()
        if position != input.count {
            throw ParseError(message: "trailing tokens")
        }
        return try checked(value)
    }

    mutating func skipWhitespace() {
        while position < input.count {
            switch input[position] {
            case 0x20, 0x09, 0x0a, 0x0d, 0x0c, 0x0b:
                position += 1
            default:
                return
            }
        }
    }

    mutating func peek() -> UInt8? {
        skipWhitespace()
        return position < input.count ? input[position] : nil
    }

    func checked(_ value: Double) throws -> Double {
        guard value.isFinite else {
            throw ParseError(message: "non-finite result")
        }
        return value
    }

    mutating func parseAdditive() throws -> Double {
        var left = try parseMultiplicative()
        while let operation = peek(), operation == 0x2b || operation == 0x2d {
            position += 1
            let right = try parseMultiplicative()
            let result = operation == 0x2b ? left + right : left - right
            left = try checked(result)
        }
        return left
    }

    mutating func parseMultiplicative() throws -> Double {
        var left = try parseUnary()
        while let operation = peek(), operation == 0x2a || operation == 0x2f || operation == 0x25 {
            position += 1
            let right = try parseUnary()
            if (operation == 0x2f || operation == 0x25) && right == 0.0 {
                throw ParseError(message: "division or remainder by zero")
            }
            let result: Double
            if operation == 0x2a {
                result = left * right
            } else if operation == 0x2f {
                result = left / right
            } else {
                result = left.truncatingRemainder(dividingBy: right)
            }
            left = try checked(result)
        }
        return left
    }

    mutating func parseUnary() throws -> Double {
        if let operation = peek(), operation == 0x2b || operation == 0x2d {
            position += 1
            let value = try parseUnary()
            return try checked(operation == 0x2b ? value : -value)
        }
        return try parsePower()
    }

    mutating func parsePower() throws -> Double {
        let base = try parsePrimary()
        if peek() == 0x5e {
            position += 1
            let exponent = try parseUnary()
            return try checked(pow(base, exponent))
        }
        return base
    }

    mutating func parsePrimary() throws -> Double {
        if peek() == 0x28 {
            position += 1
            let value = try parseAdditive()
            if peek() != 0x29 {
                throw ParseError(message: "missing closing parenthesis")
            }
            position += 1
            return value
        }
        return try parseNumber()
    }

    func isDigit(_ byte: UInt8) -> Bool {
        byte >= 0x30 && byte <= 0x39
    }

    mutating func parseNumber() throws -> Double {
        skipWhitespace()
        let start = position
        var digitsBefore = 0
        while position < input.count && isDigit(input[position]) {
            position += 1
            digitsBefore += 1
        }

        var digitsAfter = 0
        if position < input.count && input[position] == 0x2e {
            position += 1
            while position < input.count && isDigit(input[position]) {
                position += 1
                digitsAfter += 1
            }
        }

        if digitsBefore == 0 && digitsAfter == 0 {
            throw ParseError(message: "expected number or parenthesis")
        }

        if position < input.count && (input[position] == 0x65 || input[position] == 0x45) {
            position += 1
            if position < input.count && (input[position] == 0x2b || input[position] == 0x2d) {
                position += 1
            }
            let exponentStart = position
            while position < input.count && isDigit(input[position]) {
                position += 1
            }
            if position == exponentStart {
                throw ParseError(message: "malformed exponent")
            }
        }

        let token = String(decoding: input[start..<position], as: UTF8.self)
        let normalized = token.replacingOccurrences(of: ".e", with: ".0e")
            .replacingOccurrences(of: ".E", with: ".0E")
        guard let value = Double(normalized) else {
            throw ParseError(message: "invalid number")
        }
        return try checked(value)
    }
}

func fail(_ message: String) -> Never {
    FileHandle.standardError.write(Data("error: \(message)\n".utf8))
    exit(1)
}

let arguments = CommandLine.arguments
if arguments.count != 2 {
    fail("expected exactly one expression argument")
}

do {
    var parser = Parser(arguments[1])
    let result = try parser.parse()
    print(String(format: "%.17g", locale: Locale(identifier: "en_US_POSIX"), result))
} catch let error as ParseError {
    fail(error.message)
} catch {
    fail("calculation failed")
}
