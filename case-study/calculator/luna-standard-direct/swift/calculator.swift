import Foundation

enum CalcError: Error {
    case message(String)
}

struct Parser {
    private let input: [UInt8]
    private var position: Int = 0

    init(_ text: String) {
        self.input = Array(text.utf8)
    }

    private static func isDigit(_ byte: UInt8) -> Bool {
        byte >= 48 && byte <= 57
    }

    private static func isAsciiWhitespace(_ byte: UInt8) -> Bool {
        (byte >= 9 && byte <= 13) || byte == 32
    }

    private func peek() -> UInt8? {
        position < input.count ? input[position] : nil
    }

    private mutating func skipWhitespace() {
        while position < input.count && Self.isAsciiWhitespace(input[position]) {
            position += 1
        }
    }

    private static func checked(_ value: Double, message: String = "non-finite result") throws -> Double {
        guard value.isFinite else {
            throw CalcError.message(message)
        }
        return value
    }

    mutating func parse() throws -> Double {
        let value = try parseAdditive()
        skipWhitespace()
        guard position == input.count else {
            throw CalcError.message("unexpected trailing token")
        }
        return try Self.checked(value)
    }

    private mutating func parseAdditive() throws -> Double {
        var value = try parseMultiplicative()
        while true {
            skipWhitespace()
            guard let operatorByte = peek(), operatorByte == 43 || operatorByte == 45 else {
                return value
            }
            position += 1
            let right = try parseMultiplicative()
            value = operatorByte == 43 ? value + right : value - right
            value = try Self.checked(value)
        }
    }

    private mutating func parseMultiplicative() throws -> Double {
        var value = try parseUnary()
        while true {
            skipWhitespace()
            guard let operatorByte = peek(), operatorByte == 42 || operatorByte == 47 || operatorByte == 37 else {
                return value
            }
            position += 1
            let right = try parseUnary()
            if operatorByte == 47 {
                guard right != 0.0 else {
                    throw CalcError.message("division by zero")
                }
                value /= right
            } else if operatorByte == 37 {
                guard right != 0.0 else {
                    throw CalcError.message("remainder by zero")
                }
                value = value.truncatingRemainder(dividingBy: right)
            } else {
                value *= right
            }
            value = try Self.checked(value)
        }
    }

    private mutating func parseUnary() throws -> Double {
        skipWhitespace()
        guard let operatorByte = peek(), operatorByte == 43 || operatorByte == 45 else {
            return try parsePower()
        }
        position += 1
        var value = try parseUnary()
        if operatorByte == 45 {
            value = -value
        }
        return try Self.checked(value)
    }

    private mutating func parsePower() throws -> Double {
        let left = try parsePrimary()
        skipWhitespace()
        guard peek() == 94 else {
            return left
        }
        position += 1
        let right = try parseUnary()
        return try Self.checked(pow(left, right))
    }

    private mutating func parsePrimary() throws -> Double {
        skipWhitespace()
        if peek() == 40 {
            position += 1
            let value = try parseAdditive()
            skipWhitespace()
            guard peek() == 41 else {
                throw CalcError.message("expected ')'")
            }
            position += 1
            return value
        }
        if let byte = peek(), Self.isDigit(byte) || byte == 46 {
            return try parseNumber()
        }
        throw CalcError.message("expected number or '('")
    }

    private mutating func parseNumber() throws -> Double {
        let start = position
        var digits = 0
        while let byte = peek(), Self.isDigit(byte) {
            position += 1
            digits += 1
        }
        if peek() == 46 {
            position += 1
            while let byte = peek(), Self.isDigit(byte) {
                position += 1
                digits += 1
            }
        }
        guard digits > 0 else {
            throw CalcError.message("expected digits")
        }
        if peek() == 101 || peek() == 69 {
            position += 1
            if peek() == 43 || peek() == 45 {
                position += 1
            }
            let exponentStart = position
            while let byte = peek(), Self.isDigit(byte) {
                position += 1
            }
            guard position != exponentStart else {
                throw CalcError.message("expected exponent digits")
            }
        }

        guard let literal = String(bytes: input[start..<position], encoding: .utf8),
              let value = Double(literal) else {
            throw CalcError.message("invalid number")
        }
        return try Self.checked(value, message: "non-finite input")
    }
}

func writeError(_ message: String) {
    let data = Data("error: \(message)\n".utf8)
    FileHandle.standardError.write(data)
}

let arguments = Array(CommandLine.arguments.dropFirst())
guard arguments.count == 1 else {
    writeError("expected exactly one expression argument")
    exit(1)
}

do {
    var parser = Parser(arguments[0])
    let result = try parser.parse()
    print(String(result))
} catch let CalcError.message(message) {
    writeError(message)
    exit(1)
} catch {
    writeError("invalid expression")
    exit(1)
}
