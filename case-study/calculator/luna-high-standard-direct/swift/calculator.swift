import Foundation

struct CalculatorError: Error {
    let message: String
}

struct Parser {
    private let bytes: [UInt8]
    private var position = 0

    init(_ text: String) {
        bytes = Array(text.utf8)
    }

    private mutating func skipSpace() {
        while position < bytes.count {
            switch bytes[position] {
            case 0x20, 0x09, 0x0a, 0x0d, 0x0b, 0x0c:
                position += 1
            default:
                return
            }
        }
    }

    private mutating func consume(_ token: UInt8) -> Bool {
        skipSpace()
        guard position < bytes.count, bytes[position] == token else {
            return false
        }
        position += 1
        return true
    }

    private func finite(_ value: Double) throws -> Double {
        guard value.isFinite else {
            throw CalculatorError(message: "non-finite input or result")
        }
        return value
    }

    mutating func parse() throws -> Double {
        let value = try parseAdditive()
        skipSpace()
        guard position == bytes.count else {
            throw CalculatorError(message: "unexpected trailing input")
        }
        return value
    }

    private mutating func parseAdditive() throws -> Double {
        var value = try parseMultiplicative()
        while true {
            if consume(0x2b) {
                value = try finite(value + parseMultiplicative())
            } else if consume(0x2d) {
                value = try finite(value - parseMultiplicative())
            } else {
                return value
            }
        }
    }

    private mutating func parseMultiplicative() throws -> Double {
        var value = try parseUnary()
        while true {
            if consume(0x2a) {
                value = try finite(value * parseUnary())
            } else if consume(0x2f) {
                let divisor = try parseUnary()
                guard divisor != 0.0 else {
                    throw CalculatorError(message: "division by zero")
                }
                value = try finite(value / divisor)
            } else if consume(0x25) {
                let divisor = try parseUnary()
                guard divisor != 0.0 else {
                    throw CalculatorError(message: "remainder by zero")
                }
                value = try finite(value.truncatingRemainder(dividingBy: divisor))
            } else {
                return value
            }
        }
    }

    private mutating func parseUnary() throws -> Double {
        if consume(0x2b) {
            return try parseUnary()
        }
        if consume(0x2d) {
            return try finite(-(parseUnary()))
        }
        return try parsePower()
    }

    private mutating func parsePower() throws -> Double {
        let value = try parsePrimary()
        if consume(0x5e) {
            let exponent = try parseUnary()
            return try finite(Foundation.pow(value, exponent))
        }
        return value
    }

    private mutating func parsePrimary() throws -> Double {
        if consume(0x28) {
            let value = try parseAdditive()
            guard consume(0x29) else {
                throw CalculatorError(message: "expected closing parenthesis")
            }
            return value
        }
        return try parseNumber()
    }

    private mutating func parseNumber() throws -> Double {
        skipSpace()
        let start = position
        var digits = 0
        while position < bytes.count, bytes[position] >= 0x30, bytes[position] <= 0x39 {
            position += 1
            digits += 1
        }
        if position < bytes.count, bytes[position] == 0x2e {
            position += 1
            while position < bytes.count, bytes[position] >= 0x30, bytes[position] <= 0x39 {
                position += 1
                digits += 1
            }
        }
        guard digits > 0 else {
            throw CalculatorError(message: "expected number")
        }
        if position < bytes.count, bytes[position] == 0x65 || bytes[position] == 0x45 {
            position += 1
            if position < bytes.count, bytes[position] == 0x2b || bytes[position] == 0x2d {
                position += 1
            }
            let exponentStart = position
            while position < bytes.count, bytes[position] >= 0x30, bytes[position] <= 0x39 {
                position += 1
            }
            guard position != exponentStart else {
                throw CalculatorError(message: "malformed exponent")
            }
        }
        let token = String(decoding: bytes[start..<position], as: UTF8.self)
        guard let value = Double(token) else {
            throw CalculatorError(message: "invalid number")
        }
        return try finite(value)
    }
}

func fail(_ message: String) -> Never {
    FileHandle.standardError.write(Data("error: \(message)\n".utf8))
    exit(1)
}

guard CommandLine.arguments.count == 2 else {
    fail("expected exactly one expression argument")
}

do {
    var parser = Parser(CommandLine.arguments[1])
    print(try parser.parse())
} catch let error as CalculatorError {
    fail(error.message)
} catch {
    fail("invalid expression")
}
