import Foundation

enum CalculatorError: Error, CustomStringConvertible {
    case message(String)
    var description: String {
        switch self { case .message(let text): return text }
    }
}

struct Parser {
    let input: [UInt8]
    var pos = 0

    init(_ text: String) { input = Array(text.utf8) }

    mutating func skipSpace() {
        while pos < input.count && [9, 10, 11, 12, 13, 32].contains(input[pos]) { pos += 1 }
    }

    mutating func take(_ token: UInt8) -> Bool {
        skipSpace()
        if pos < input.count && input[pos] == token { pos += 1; return true }
        return false
    }

    func checked(_ value: Double) throws -> Double {
        guard value.isFinite else { throw CalculatorError.message("non-finite result") }
        return value
    }

    mutating func parse() throws -> Double {
        let value = try additive()
        skipSpace()
        guard pos == input.count else { throw CalculatorError.message("unexpected trailing input") }
        return value
    }

    mutating func additive() throws -> Double {
        var value = try multiplicative()
        while true {
            if take(43) { value = try checked(value + multiplicative()) }
            else if take(45) { value = try checked(value - multiplicative()) }
            else { return value }
        }
    }

    mutating func multiplicative() throws -> Double {
        var value = try unary()
        while true {
            if take(42) { value = try checked(value * unary()) }
            else if take(47) {
                let divisor = try unary()
                guard divisor != 0 else { throw CalculatorError.message("division by zero") }
                value = try checked(value / divisor)
            } else if take(37) {
                let divisor = try unary()
                guard divisor != 0 else { throw CalculatorError.message("remainder by zero") }
                value = try checked(value.truncatingRemainder(dividingBy: divisor))
            } else { return value }
        }
    }

    mutating func unary() throws -> Double {
        if take(43) { return try unary() }
        if take(45) { return try checked(-unary()) }
        return try power()
    }

    mutating func power() throws -> Double {
        let base = try primary()
        return take(94) ? try checked(Foundation.pow(base, unary())) : base
    }

    mutating func primary() throws -> Double {
        if take(40) {
            let value = try additive()
            guard take(41) else { throw CalculatorError.message("expected ')'") }
            return value
        }
        return try number()
    }

    mutating func number() throws -> Double {
        skipSpace()
        let start = pos
        var digits = 0
        while pos < input.count && input[pos] >= 48 && input[pos] <= 57 { pos += 1; digits += 1 }
        if pos < input.count && input[pos] == 46 {
            pos += 1
            while pos < input.count && input[pos] >= 48 && input[pos] <= 57 { pos += 1; digits += 1 }
        }
        guard digits > 0 else { throw CalculatorError.message("expected number") }
        if pos < input.count && (input[pos] == 101 || input[pos] == 69) {
            pos += 1
            if pos < input.count && (input[pos] == 43 || input[pos] == 45) { pos += 1 }
            let exponentStart = pos
            while pos < input.count && input[pos] >= 48 && input[pos] <= 57 { pos += 1 }
            guard pos > exponentStart else { throw CalculatorError.message("malformed exponent") }
        }
        let token = String(decoding: input[start..<pos], as: UTF8.self)
        guard let value = Double(token) else { throw CalculatorError.message("invalid number") }
        guard value.isFinite else { throw CalculatorError.message("non-finite input") }
        return value
    }
}

guard CommandLine.arguments.count == 2 else {
    FileHandle.standardError.write(Data("error: expected exactly one expression\n".utf8))
    exit(1)
}

do {
    var parser = Parser(CommandLine.arguments[1])
    print(try parser.parse())
} catch {
    FileHandle.standardError.write(Data("error: \(error)\n".utf8))
    exit(1)
}
