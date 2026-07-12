import Foundation

enum CalculatorError: Error {
    case message(String)
}

struct Parser {
    private let input: [UInt8]
    private var position: Int = 0

    init(_ source: String) {
        input = Array(source.utf8)
    }

    private mutating func skipWhitespace() {
        while position < input.count {
            switch input[position] {
            case 9, 10, 11, 12, 13, 32:
                position += 1
            default:
                return
            }
        }
    }

    private mutating func take(_ byte: UInt8) -> Bool {
        skipWhitespace()
        guard position < input.count, input[position] == byte else { return false }
        position += 1
        return true
    }

    private static func finite(_ value: Double) throws -> Double {
        guard value.isFinite else { throw CalculatorError.message("non-finite result") }
        return value
    }

    mutating func evaluate() throws -> Double {
        let result = try parseSum()
        skipWhitespace()
        guard position == input.count else {
            throw CalculatorError.message("unexpected trailing input")
        }
        return result
    }

    private mutating func parseSum() throws -> Double {
        var result = try parseProduct()
        while true {
            if take(43) {
                result = try Self.finite(result + parseProduct())
            } else if take(45) {
                result = try Self.finite(result - parseProduct())
            } else {
                return result
            }
        }
    }

    private mutating func parseProduct() throws -> Double {
        var result = try parseUnary()
        while true {
            if take(42) {
                result = try Self.finite(result * parseUnary())
            } else if take(47) {
                let divisor = try parseUnary()
                guard divisor != 0 else { throw CalculatorError.message("division by zero") }
                result = try Self.finite(result / divisor)
            } else if take(37) {
                let divisor = try parseUnary()
                guard divisor != 0 else { throw CalculatorError.message("remainder by zero") }
                result = try Self.finite(result.truncatingRemainder(dividingBy: divisor))
            } else {
                return result
            }
        }
    }

    private mutating func parseUnary() throws -> Double {
        if take(43) { return try parseUnary() }
        if take(45) { return try Self.finite(-parseUnary()) }
        return try parsePower()
    }

    private mutating func parsePower() throws -> Double {
        let base = try parsePrimary()
        if take(94) {
            let exponent = try parseUnary()
            return try Self.finite(Foundation.pow(base, exponent))
        }
        return base
    }

    private mutating func parsePrimary() throws -> Double {
        if take(40) {
            let result = try parseSum()
            guard take(41) else { throw CalculatorError.message("expected closing parenthesis") }
            return result
        }
        return try parseNumber()
    }

    private mutating func parseNumber() throws -> Double {
        skipWhitespace()
        let start = position
        var digitCount = 0

        while position < input.count && input[position] >= 48 && input[position] <= 57 {
            position += 1
            digitCount += 1
        }
        if position < input.count && input[position] == 46 {
            position += 1
            while position < input.count && input[position] >= 48 && input[position] <= 57 {
                position += 1
                digitCount += 1
            }
        }
        guard digitCount > 0 else { throw CalculatorError.message("expected number") }

        if position < input.count && (input[position] == 101 || input[position] == 69) {
            position += 1
            if position < input.count && (input[position] == 43 || input[position] == 45) {
                position += 1
            }
            let exponentStart = position
            while position < input.count && input[position] >= 48 && input[position] <= 57 {
                position += 1
            }
            guard position != exponentStart else {
                throw CalculatorError.message("malformed exponent")
            }
        }

        let token = String(decoding: input[start..<position], as: UTF8.self)
        guard let value = Double(token) else { throw CalculatorError.message("invalid number") }
        return try Self.finite(value)
    }
}

func reportError(_ message: String) -> Never {
    FileHandle.standardError.write(Data("error: \(message)\n".utf8))
    exit(1)
}

guard CommandLine.arguments.count == 2 else {
    reportError("expected exactly one expression argument")
}

do {
    var parser = Parser(CommandLine.arguments[1])
    let result = try parser.evaluate()
    print(String(result))
} catch let CalculatorError.message(message) {
    reportError(message)
} catch {
    reportError("calculation failed")
}
