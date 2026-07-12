import Foundation

enum CalcError: Error, CustomStringConvertible {
    case message(String)
    var description: String {
        switch self { case let .message(text): return text }
    }
}

func checked(_ value: Double) throws -> Double {
    guard value.isFinite else { throw CalcError.message("non-finite value") }
    return value
}

final class Parser {
    let text: [UInt8]
    var pos = 0
    init(_ input: String) { text = Array(input.utf8) }
    func skip() { while pos < text.count && (text[pos] == 32 || (text[pos] >= 9 && text[pos] <= 13)) { pos += 1 } }
    func take(_ byte: UInt8) -> Bool { skip(); if pos < text.count && text[pos] == byte { pos += 1; return true }; return false }
    func parse() throws -> Double { let value = try expression(); skip(); guard pos == text.count else { throw CalcError.message("unexpected token") }; return value }
    func expression() throws -> Double {
        var value = try term()
        while true {
            if take(43) { value = try checked(value + term()) }
            else if take(45) { value = try checked(value - term()) }
            else { return value }
        }
    }
    func term() throws -> Double {
        var value = try unary()
        while true {
            if take(42) { value = try checked(value * unary()) }
            else if take(47) { let rhs = try unary(); guard rhs != 0 else { throw CalcError.message("division by zero") }; value = try checked(value / rhs) }
            else if take(37) { let rhs = try unary(); guard rhs != 0 else { throw CalcError.message("remainder by zero") }; value = try checked(value.truncatingRemainder(dividingBy: rhs)) }
            else { return value }
        }
    }
    func unary() throws -> Double { if take(43) { return try unary() }; if take(45) { return try checked(-unary()) }; return try power() }
    func power() throws -> Double { var value = try primary(); if take(94) { value = try checked(pow(value, unary())) }; return value }
    func primary() throws -> Double {
        if take(40) { let value = try expression(); guard take(41) else { throw CalcError.message("expected ')'") }; return value }
        return try number()
    }
    func number() throws -> Double {
        skip(); let start = pos; var digits = 0
        while pos < text.count && text[pos] >= 48 && text[pos] <= 57 { pos += 1; digits += 1 }
        if pos < text.count && text[pos] == 46 { pos += 1; while pos < text.count && text[pos] >= 48 && text[pos] <= 57 { pos += 1; digits += 1 } }
        guard digits > 0 else { throw CalcError.message("expected number") }
        if pos < text.count && (text[pos] == 101 || text[pos] == 69) {
            pos += 1; if pos < text.count && (text[pos] == 43 || text[pos] == 45) { pos += 1 }
            let exponent = pos; while pos < text.count && text[pos] >= 48 && text[pos] <= 57 { pos += 1 }
            guard pos != exponent else { throw CalcError.message("malformed exponent") }
        }
        guard let value = Double(String(decoding: text[start..<pos], as: UTF8.self)) else { throw CalcError.message("invalid number") }
        return try checked(value)
    }
}

do {
    guard CommandLine.arguments.count == 2 else { throw CalcError.message("expected exactly one expression") }
    print(try Parser(CommandLine.arguments[1]).parse())
} catch {
    FileHandle.standardError.write(Data("error: \(error)\n".utf8))
    exit(1)
}
