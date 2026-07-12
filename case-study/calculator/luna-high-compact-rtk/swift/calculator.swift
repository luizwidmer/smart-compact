import Foundation

enum CalcError: Error {
    case message(String)
}

struct Parser {
    let text: [UInt8]
    var pos = 0

    init(_ input: String) { text = Array(input.utf8) }

    mutating func whitespace() {
        while pos < text.count && [32, 9, 10, 13, 11, 12].contains(text[pos]) { pos += 1 }
    }

    mutating func number() throws -> Double {
        whitespace()
        let start = pos
        var digits = 0
        while pos < text.count && text[pos] >= 48 && text[pos] <= 57 { pos += 1; digits += 1 }
        if pos < text.count && text[pos] == 46 {
            pos += 1
            while pos < text.count && text[pos] >= 48 && text[pos] <= 57 { pos += 1; digits += 1 }
        }
        if digits == 0 { pos = start; throw CalcError.message("expected number") }
        if pos < text.count && (text[pos] == 101 || text[pos] == 69) {
            pos += 1
            if pos < text.count && (text[pos] == 43 || text[pos] == 45) { pos += 1 }
            let exponentStart = pos
            while pos < text.count && text[pos] >= 48 && text[pos] <= 57 { pos += 1 }
            if pos == exponentStart { throw CalcError.message("malformed exponent") }
        }
        let raw = String(decoding: text[start..<pos], as: UTF8.self)
        guard let value = Double(raw), value.isFinite else { throw CalcError.message("non-finite number") }
        return value
    }

    mutating func primary() throws -> Double {
        whitespace()
        if pos < text.count && text[pos] == 40 {
            pos += 1
            let value = try additive()
            whitespace()
            if pos >= text.count || text[pos] != 41 { throw CalcError.message("expected closing parenthesis") }
            pos += 1
            return value
        }
        return try number()
    }

    mutating func power() throws -> Double {
        var value = try primary()
        whitespace()
        if pos < text.count && text[pos] == 94 {
            pos += 1
            let exponent = try unary()
            value = Foundation.pow(value, exponent)
            if !value.isFinite { throw CalcError.message("non-finite result") }
        }
        return value
    }

    mutating func unary() throws -> Double {
        whitespace()
        if pos < text.count && (text[pos] == 43 || text[pos] == 45) {
            let negative = text[pos] == 45
            pos += 1
            let value = try unary()
            return negative ? -value : value
        }
        return try power()
    }

    mutating func multiplicative() throws -> Double {
        var value = try unary()
        while true {
            whitespace()
            if pos >= text.count || ![42, 47, 37].contains(text[pos]) { return value }
            let op = text[pos]
            pos += 1
            let right = try unary()
            if right == 0 { throw CalcError.message("division by zero") }
            if op == 42 { value *= right }
            else if op == 47 { value /= right }
            else { value = value.truncatingRemainder(dividingBy: right) }
            if !value.isFinite { throw CalcError.message("non-finite result") }
        }
    }

    mutating func additive() throws -> Double {
        var value = try multiplicative()
        while true {
            whitespace()
            if pos >= text.count || (text[pos] != 43 && text[pos] != 45) { return value }
            let op = text[pos]
            pos += 1
            let right = try multiplicative()
            value = op == 43 ? value + right : value - right
            if !value.isFinite { throw CalcError.message("non-finite result") }
        }
    }

    mutating func parse() throws -> Double {
        whitespace()
        if pos == text.count { throw CalcError.message("empty expression") }
        let value = try additive()
        whitespace()
        if pos != text.count { throw CalcError.message("trailing tokens") }
        return value
    }
}

do {
    let args = CommandLine.arguments
    guard args.count == 2 else { throw CalcError.message("expected exactly one expression") }
    var parser = Parser(args[1])
    print(try parser.parse())
} catch let CalcError.message(message) {
    FileHandle.standardError.write(Data("error: \(message)\n".utf8))
    exit(1)
} catch {
    FileHandle.standardError.write(Data("error: calculator failure\n".utf8))
    exit(1)
}
