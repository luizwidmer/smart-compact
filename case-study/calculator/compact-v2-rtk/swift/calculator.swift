import Foundation

struct CalculatorError: Error {
    let message: String
}

final class Parser {
    private let input: [UInt8]
    private var pos = 0

    init(_ text: String) { input = Array(text.utf8) }

    private func skipSpace() {
        while pos < input.count && [9, 10, 11, 12, 13, 32].contains(input[pos]) { pos += 1 }
    }

    private func take(_ token: UInt8) -> Bool {
        skipSpace()
        if pos < input.count && input[pos] == token { pos += 1; return true }
        return false
    }

    private func checked(_ value: Double) throws -> Double {
        guard value.isFinite else { throw CalculatorError(message: "non-finite result") }
        return value
    }

    func parse() throws -> Double {
        let value = try expression()
        skipSpace()
        guard pos == input.count else { throw CalculatorError(message: "unexpected token") }
        return value
    }

    private func expression() throws -> Double {
        var value = try term()
        while true {
            if take(43) { value = try checked(value + term()) }
            else if take(45) { value = try checked(value - term()) }
            else { return value }
        }
    }

    private func term() throws -> Double {
        var value = try unary()
        while true {
            if take(42) { value = try checked(value * unary()) }
            else if take(47) {
                let rhs = try unary()
                guard rhs != 0 else { throw CalculatorError(message: "division by zero") }
                value = try checked(value / rhs)
            } else if take(37) {
                let rhs = try unary()
                guard rhs != 0 else { throw CalculatorError(message: "remainder by zero") }
                value = try checked(value.truncatingRemainder(dividingBy: rhs))
            } else { return value }
        }
    }

    private func unary() throws -> Double {
        if take(43) { return try unary() }
        if take(45) { return try checked(-unary()) }
        return try power()
    }

    private func power() throws -> Double {
        var value = try primary()
        if take(94) { value = try checked(Foundation.pow(value, unary())) }
        return value
    }

    private func primary() throws -> Double {
        if take(40) {
            let value = try expression()
            guard take(41) else { throw CalculatorError(message: "missing closing parenthesis") }
            return value
        }
        return try number()
    }

    private func number() throws -> Double {
        skipSpace()
        let start = pos
        var digits = 0
        while pos < input.count && input[pos] >= 48 && input[pos] <= 57 { pos += 1; digits += 1 }
        if pos < input.count && input[pos] == 46 {
            pos += 1
            while pos < input.count && input[pos] >= 48 && input[pos] <= 57 { pos += 1; digits += 1 }
        }
        guard digits > 0 else { throw CalculatorError(message: "expected number") }
        if pos < input.count && (input[pos] == 101 || input[pos] == 69) {
            pos += 1
            if pos < input.count && (input[pos] == 43 || input[pos] == 45) { pos += 1 }
            let exponent = pos
            while pos < input.count && input[pos] >= 48 && input[pos] <= 57 { pos += 1 }
            guard pos > exponent else { throw CalculatorError(message: "malformed exponent") }
        }
        let token = String(decoding: input[start..<pos], as: UTF8.self)
        guard let value = Double(token) else { throw CalculatorError(message: "invalid number") }
        return try checked(value)
    }
}

do {
    guard CommandLine.arguments.count == 2 else { throw CalculatorError(message: "expected exactly one expression") }
    print(try Parser(CommandLine.arguments[1]).parse())
} catch let error as CalculatorError {
    FileHandle.standardError.write(Data("error: \(error.message)\n".utf8))
    exit(1)
} catch {
    FileHandle.standardError.write(Data("error: invalid expression\n".utf8))
    exit(1)
}
