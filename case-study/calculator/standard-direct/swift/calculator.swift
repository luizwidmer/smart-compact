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
        while position < input.count && [9, 10, 11, 12, 13, 32].contains(input[position]) {
            position += 1
        }
    }

    private func consume(_ byte: UInt8) -> Bool {
        skipSpace()
        if position < input.count && input[position] == byte {
            position += 1
            return true
        }
        return false
    }

    private func finite(_ value: Double) throws -> Double {
        guard value.isFinite else { throw CalculatorError.message("non-finite result") }
        return value
    }

    func parse() throws -> Double {
        let value = try additive()
        skipSpace()
        guard position == input.count else { throw CalculatorError.message("unexpected trailing input") }
        return value
    }

    private func additive() throws -> Double {
        var value = try multiplicative()
        while true {
            if consume(43) { value = try finite(value + multiplicative()) }
            else if consume(45) { value = try finite(value - multiplicative()) }
            else { return value }
        }
    }

    private func multiplicative() throws -> Double {
        var value = try unary()
        while true {
            if consume(42) { value = try finite(value * unary()) }
            else if consume(47) {
                let divisor = try unary()
                guard divisor != 0 else { throw CalculatorError.message("division by zero") }
                value = try finite(value / divisor)
            } else if consume(37) {
                let divisor = try unary()
                guard divisor != 0 else { throw CalculatorError.message("remainder by zero") }
                value = try finite(value.truncatingRemainder(dividingBy: divisor))
            } else { return value }
        }
    }

    private func unary() throws -> Double {
        if consume(43) { return try unary() }
        if consume(45) { return try finite(-unary()) }
        return try power()
    }

    private func power() throws -> Double {
        var value = try primary()
        if consume(94) { value = try finite(Foundation.pow(value, unary())) }
        return value
    }

    private func primary() throws -> Double {
        if consume(40) {
            let value = try additive()
            guard consume(41) else { throw CalculatorError.message("expected closing parenthesis") }
            return value
        }
        return try number()
    }

    private func number() throws -> Double {
        skipSpace()
        let start = position
        var digits = 0
        while position < input.count && input[position] >= 48 && input[position] <= 57 {
            position += 1; digits += 1
        }
        if position < input.count && input[position] == 46 {
            position += 1
            while position < input.count && input[position] >= 48 && input[position] <= 57 {
                position += 1; digits += 1
            }
        }
        guard digits > 0 else { throw CalculatorError.message("expected number") }
        if position < input.count && (input[position] == 101 || input[position] == 69) {
            position += 1
            if position < input.count && (input[position] == 43 || input[position] == 45) { position += 1 }
            let exponentStart = position
            while position < input.count && input[position] >= 48 && input[position] <= 57 { position += 1 }
            guard position > exponentStart else { throw CalculatorError.message("malformed exponent") }
        }
        let token = String(decoding: input[start..<position], as: UTF8.self)
        guard let value = Double(token) else { throw CalculatorError.message("invalid number") }
        return try finite(value)
    }
}

guard CommandLine.arguments.count == 2 else {
    FileHandle.standardError.write(Data("error: expected exactly one expression argument\n".utf8))
    exit(1)
}

do {
    print(try Parser(CommandLine.arguments[1]).parse())
} catch {
    FileHandle.standardError.write(Data("error: \(error)\n".utf8))
    exit(1)
}
