import Foundation

enum CalculatorError: Error {
    case message(String)
}

struct Parser {
    private let bytes: [UInt8]
    private var position: Int = 0

    init(_ text: String) {
        self.bytes = Array(text.utf8)
    }

    mutating func parse() throws -> Double {
        let value = try parseExpression()
        skipWhitespace()
        if position != bytes.count { throw CalculatorError.message("trailing tokens") }
        return value
    }

    private mutating func skipWhitespace() {
        while position < bytes.count && [32, 9, 10, 13, 11, 12].contains(bytes[position]) {
            position += 1
        }
    }

    private mutating func match(_ token: UInt8) -> Bool {
        skipWhitespace()
        if position < bytes.count && bytes[position] == token {
            position += 1
            return true
        }
        return false
    }

    private mutating func parseNumber() throws -> Double {
        skipWhitespace()
        let start = position
        var digits = 0
        while position < bytes.count && bytes[position] >= 48 && bytes[position] <= 57 {
            position += 1
            digits += 1
        }
        if position < bytes.count && bytes[position] == 46 {
            position += 1
            while position < bytes.count && bytes[position] >= 48 && bytes[position] <= 57 {
                position += 1
                digits += 1
            }
        }
        if digits == 0 { throw CalculatorError.message("expected number") }
        if position < bytes.count && (bytes[position] == 101 || bytes[position] == 69) {
            position += 1
            if position < bytes.count && (bytes[position] == 43 || bytes[position] == 45) { position += 1 }
            let exponentStart = position
            while position < bytes.count && bytes[position] >= 48 && bytes[position] <= 57 { position += 1 }
            if exponentStart == position { throw CalculatorError.message("invalid exponent") }
        }
        let token = String(decoding: bytes[start..<position], as: UTF8.self)
        guard let value = Double(token), value.isFinite else {
            throw CalculatorError.message("non-finite number")
        }
        return value
    }

    private mutating func parsePrimary() throws -> Double {
        if match(40) {
            let value = try parseExpression()
            if !match(41) { throw CalculatorError.message("expected ')' ") }
            return value
        }
        return try parseNumber()
    }

    private mutating func parsePower() throws -> Double {
        let value = try parsePrimary()
        if match(94) {
            let result = pow(value, try parseUnary())
            if !result.isFinite { throw CalculatorError.message("non-finite result") }
            return result
        }
        return value
    }

    private mutating func parseUnary() throws -> Double {
        if match(43) { return try parseUnary() }
        if match(45) {
            let result = -(try parseUnary())
            if !result.isFinite { throw CalculatorError.message("non-finite result") }
            return result
        }
        return try parsePower()
    }

    private mutating func parseMultiplicative() throws -> Double {
        var value = try parseUnary()
        while true {
            if match(42) {
                value *= try parseUnary()
            } else if match(47) {
                let divisor = try parseUnary()
                if divisor == 0 { throw CalculatorError.message("division by zero") }
                value /= divisor
            } else if match(37) {
                let divisor = try parseUnary()
                if divisor == 0 { throw CalculatorError.message("remainder by zero") }
                value = value.truncatingRemainder(dividingBy: divisor)
            } else {
                break
            }
            if !value.isFinite { throw CalculatorError.message("non-finite result") }
        }
        return value
    }

    private mutating func parseExpression() throws -> Double {
        var value = try parseMultiplicative()
        while true {
            if match(43) {
                value += try parseMultiplicative()
            } else if match(45) {
                value -= try parseMultiplicative()
            } else {
                break
            }
            if !value.isFinite { throw CalculatorError.message("non-finite result") }
        }
        return value
    }
}

guard CommandLine.arguments.count == 2 else {
    fputs("error: expected exactly one expression argument\n", stderr)
    exit(1)
}

do {
    var parser = Parser(CommandLine.arguments[1])
    print(try parser.parse())
} catch CalculatorError.message(let message) {
    fputs("error: \(message)\n", stderr)
    exit(1)
} catch {
    fputs("error: calculation failed\n", stderr)
    exit(1)
}
