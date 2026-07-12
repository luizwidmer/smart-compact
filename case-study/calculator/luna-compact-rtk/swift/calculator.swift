import Foundation

struct CalculatorError: Error {
    let message: String
}

struct Parser {
    private let input: [UInt8]
    private var position: Int = 0

    init(_ expression: String) {
        input = Array(expression.utf8)
    }

    mutating func parse() throws -> Double {
        let value = try parseAddition()
        skipWhitespace()
        if position != input.count {
            throw CalculatorError(message: "unexpected trailing token")
        }
        return value
    }

    private mutating func parseAddition() throws -> Double {
        var value = try parseMultiplication()
        while true {
            if consume(43) {
                let right = try parseMultiplication()
                value = try checked(value + right)
            } else if consume(45) {
                let right = try parseMultiplication()
                value = try checked(value - right)
            } else {
                return value
            }
        }
    }

    private mutating func parseMultiplication() throws -> Double {
        var value = try parseUnary()
        while true {
            if consume(42) {
                let right = try parseUnary()
                value = try checked(value * right)
            } else if consume(47) {
                let right = try parseUnary()
                if right == 0.0 {
                    throw CalculatorError(message: "division by zero")
                }
                value = try checked(value / right)
            } else if consume(37) {
                let right = try parseUnary()
                if right == 0.0 {
                    throw CalculatorError(message: "remainder by zero")
                }
                value = try checked(value.truncatingRemainder(dividingBy: right))
            } else {
                return value
            }
        }
    }

    private mutating func parseUnary() throws -> Double {
        if consume(43) {
            return try parseUnary()
        }
        if consume(45) {
            let value = try parseUnary()
            return -value
        }
        return try parsePower()
    }

    private mutating func parsePower() throws -> Double {
        let value = try parsePrimary()
        if consume(94) {
            let exponent = try parseUnary()
            return try checked(pow(value, exponent))
        }
        return value
    }

    private mutating func parsePrimary() throws -> Double {
        skipWhitespace()
        guard let byte = peek() else {
            throw CalculatorError(message: "expected a number or parenthesized expression")
        }

        if byte == 40 {
            position += 1
            let value = try parseAddition()
            if !consume(41) {
                throw CalculatorError(message: "missing closing parenthesis")
            }
            return value
        }

        if isDigit(byte) || byte == 46 {
            return try parseNumber()
        }
        throw CalculatorError(message: "expected a number or parenthesized expression")
    }

    private mutating func parseNumber() throws -> Double {
        let start = position
        var digitsBeforeDecimal = 0
        while let byte = peek(), isDigit(byte) {
            position += 1
            digitsBeforeDecimal += 1
        }

        var digitsAfterDecimal = 0
        if peek() == 46 {
            position += 1
            while let byte = peek(), isDigit(byte) {
                position += 1
                digitsAfterDecimal += 1
            }
        }

        if digitsBeforeDecimal == 0 && digitsAfterDecimal == 0 {
            throw CalculatorError(message: "invalid number")
        }

        if let byte = peek(), byte == 101 || byte == 69 {
            position += 1
            if let sign = peek(), sign == 43 || sign == 45 {
                position += 1
            }
            var exponentDigits = 0
            while let digit = peek(), isDigit(digit) {
                position += 1
                exponentDigits += 1
            }
            if exponentDigits == 0 {
                throw CalculatorError(message: "invalid exponent")
            }
        }

        let literal = String(decoding: input[start..<position], as: UTF8.self)
        guard let value = Double(literal) else {
            throw CalculatorError(message: "invalid number")
        }
        return try checked(value)
    }

    private mutating func consume(_ token: UInt8) -> Bool {
        skipWhitespace()
        guard let byte = peek(), byte == token else {
            return false
        }
        position += 1
        return true
    }

    private mutating func skipWhitespace() {
        while let byte = peek(), isWhitespace(byte) {
            position += 1
        }
    }

    private func peek() -> UInt8? {
        guard position < input.count else {
            return nil
        }
        return input[position]
    }

    private func isDigit(_ byte: UInt8) -> Bool {
        byte >= 48 && byte <= 57
    }

    private func isWhitespace(_ byte: UInt8) -> Bool {
        byte == 32 || byte == 9 || byte == 10 || byte == 13 || byte == 11 || byte == 12
    }

    private func checked(_ value: Double) throws -> Double {
        guard value.isFinite else {
            throw CalculatorError(message: "non-finite result")
        }
        return value
    }
}

func reportError(_ message: String) -> Never {
    let output = Data("error: \(message)\n".utf8)
    FileHandle.standardError.write(output)
    exit(1)
}

let arguments = CommandLine.arguments
guard arguments.count == 2 else {
    reportError("expected exactly one expression argument")
}

do {
    var parser = Parser(arguments[1])
    let result = try parser.parse()
    print(result)
} catch let error as CalculatorError {
    reportError(error.message)
} catch {
    reportError("invalid expression")
}
