import Foundation

enum CalculatorError: Error, CustomStringConvertible {
    case message(String)
    var description: String {
        switch self { case .message(let text): return text }
    }
}

final class Parser {
    private let input: [UInt8]
    private var pos = 0

    init(_ text: String) { input = Array(text.utf8) }

    private func skipWhitespace() {
        while pos < input.count && [9, 10, 11, 12, 13, 32].contains(input[pos]) { pos += 1 }
    }

    private func consume(_ token: UInt8) -> Bool {
        skipWhitespace()
        if pos < input.count && input[pos] == token { pos += 1; return true }
        return false
    }

    private func checked(_ value: Double) throws -> Double {
        guard value.isFinite else { throw CalculatorError.message("non-finite result") }
        return value
    }

    func parse() throws -> Double {
        let value = try expression()
        skipWhitespace()
        guard pos == input.count else { throw CalculatorError.message("unexpected trailing input") }
        return value
    }

    private func expression() throws -> Double {
        var value = try term()
        while true {
            if consume(43) { value = try checked(value + term()) }
            else if consume(45) { value = try checked(value - term()) }
            else { return value }
        }
    }

    private func term() throws -> Double {
        var value = try unary()
        while true {
            if consume(42) { value = try checked(value * unary()) }
            else if consume(47) {
                let divisor = try unary()
                guard divisor != 0 else { throw CalculatorError.message("division by zero") }
                value = try checked(value / divisor)
            } else if consume(37) {
                let divisor = try unary()
                guard divisor != 0 else { throw CalculatorError.message("remainder by zero") }
                value = try checked(value.truncatingRemainder(dividingBy: divisor))
            } else { return value }
        }
    }

    private func unary() throws -> Double {
        if consume(43) { return try checked(unary()) }
        if consume(45) { return try checked(-unary()) }
        return try power()
    }

    private func power() throws -> Double {
        let base = try primary()
        if consume(94) { return try checked(Foundation.pow(base, unary())) }
        return base
    }

    private func primary() throws -> Double {
        if consume(40) {
            let value = try expression()
            guard consume(41) else { throw CalculatorError.message("expected ')'") }
            return value
        }
        return try number()
    }

    private func number() throws -> Double {
        skipWhitespace()
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
        guard let text = String(bytes: input[start..<pos], encoding: .ascii), let value = Double(text) else {
            throw CalculatorError.message("invalid number")
        }
        return try checked(value)
    }
}

let arguments = CommandLine.arguments
guard arguments.count == 2 else {
    FileHandle.standardError.write(Data("error: expected exactly one expression argument\n".utf8))
    exit(1)
}

do {
    print(try Parser(arguments[1]).parse())
} catch {
    FileHandle.standardError.write(Data("error: \(error)\n".utf8))
    exit(1)
}
