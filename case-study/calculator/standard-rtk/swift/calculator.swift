import Foundation

enum CalculatorError: Error, CustomStringConvertible {
    case message(String)
    var description: String {
        switch self { case .message(let text): return text }
    }
}

final class Parser {
    private let input: [UInt8]
    private var position = 0

    init(_ text: String) { input = Array(text.utf8) }

    private func skipSpace() {
        while position < input.count && [9, 10, 11, 12, 13, 32].contains(input[position]) { position += 1 }
    }

    private func take(_ byte: UInt8) -> Bool {
        skipSpace()
        if position < input.count && input[position] == byte { position += 1; return true }
        return false
    }

    func parse() throws -> Double {
        let value = try additive()
        skipSpace()
        if position != input.count { throw CalculatorError.message("unexpected token") }
        return value
    }

    private func additive() throws -> Double {
        var value = try multiplicative()
        while true {
            if take(43) { value = try checked(value + multiplicative()) }
            else if take(45) { value = try checked(value - multiplicative()) }
            else { return value }
        }
    }

    private func multiplicative() throws -> Double {
        var value = try unary()
        while true {
            if take(42) { value = try checked(value * unary()) }
            else if take(47) {
                let divisor = try unary()
                if divisor == 0 { throw CalculatorError.message("division by zero") }
                value = try checked(value / divisor)
            } else if take(37) {
                let divisor = try unary()
                if divisor == 0 { throw CalculatorError.message("remainder by zero") }
                value = try checked(value.truncatingRemainder(dividingBy: divisor))
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
            let value = try additive()
            if !take(41) { throw CalculatorError.message("expected closing parenthesis") }
            return value
        }
        return try number()
    }

    private func number() throws -> Double {
        skipSpace()
        let start = position
        var before = 0
        while position < input.count && input[position] >= 48 && input[position] <= 57 { position += 1; before += 1 }
        var after = 0
        if position < input.count && input[position] == 46 {
            position += 1
            while position < input.count && input[position] >= 48 && input[position] <= 57 { position += 1; after += 1 }
        }
        if before == 0 && after == 0 { throw CalculatorError.message("expected number") }
        if position < input.count && (input[position] == 101 || input[position] == 69) {
            position += 1
            if position < input.count && (input[position] == 43 || input[position] == 45) { position += 1 }
            let exponentStart = position
            while position < input.count && input[position] >= 48 && input[position] <= 57 { position += 1 }
            if position == exponentStart { throw CalculatorError.message("malformed exponent") }
        }
        guard let token = String(bytes: input[start..<position], encoding: .utf8), let value = Double(token) else {
            throw CalculatorError.message("invalid number")
        }
        return try checked(value)
    }
}

func checked(_ value: Double) throws -> Double {
    if !value.isFinite { throw CalculatorError.message("non-finite result") }
    return value
}

if CommandLine.arguments.count != 2 {
    FileHandle.standardError.write(Data("error: expected exactly one expression\n".utf8))
    exit(1)
}
do {
    print(try Parser(CommandLine.arguments[1]).parse())
} catch {
    FileHandle.standardError.write(Data("error: \(error)\n".utf8))
    exit(1)
}
