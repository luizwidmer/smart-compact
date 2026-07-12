import Foundation

enum CalcError: Error, CustomStringConvertible {
    case message(String)
    var description: String { if case .message(let text) = self { return text }; return "error" }
}

final class Parser {
    let input: [UInt8]; var pos = 0
    init(_ text: String) { input = Array(text.utf8) }
    func space() { while pos < input.count && [9, 10, 11, 12, 13, 32].contains(input[pos]) { pos += 1 } }
    func take(_ ch: UInt8) -> Bool { space(); if pos < input.count && input[pos] == ch { pos += 1; return true }; return false }
    func checked(_ value: Double) throws -> Double { guard value.isFinite else { throw CalcError.message("non-finite value") }; return value }
    func expression() throws -> Double {
        var value = try product()
        while true { if take(43) { value = try checked(value + product()) } else if take(45) { value = try checked(value - product()) } else { return value } }
    }
    func product() throws -> Double {
        var value = try unary()
        while true {
            if take(42) { value = try checked(value * unary()) }
            else if take(47) { let rhs = try unary(); if rhs == 0 { throw CalcError.message("division by zero") }; value = try checked(value / rhs) }
            else if take(37) { let rhs = try unary(); if rhs == 0 { throw CalcError.message("remainder by zero") }; value = try checked(value.truncatingRemainder(dividingBy: rhs)) }
            else { return value }
        }
    }
    func unary() throws -> Double { if take(43) { return try unary() }; if take(45) { return try checked(-unary()) }; return try power() }
    func power() throws -> Double { var value = try primary(); if take(94) { value = try checked(Foundation.pow(value, unary())) }; return value }
    func primary() throws -> Double {
        if take(40) { let value = try expression(); if !take(41) { throw CalcError.message("expected closing parenthesis") }; return value }
        space(); let start = pos; var digits = false
        while pos < input.count && input[pos] >= 48 && input[pos] <= 57 { pos += 1; digits = true }
        if pos < input.count && input[pos] == 46 { pos += 1; while pos < input.count && input[pos] >= 48 && input[pos] <= 57 { pos += 1; digits = true } }
        if !digits { throw CalcError.message("expected number") }
        if pos < input.count && (input[pos] == 101 || input[pos] == 69) { pos += 1; if pos < input.count && (input[pos] == 43 || input[pos] == 45) { pos += 1 }; let exponent = pos; while pos < input.count && input[pos] >= 48 && input[pos] <= 57 { pos += 1 }; if pos == exponent { throw CalcError.message("malformed exponent") } }
        guard let text = String(bytes: input[start..<pos], encoding: .utf8), let value = Double(text) else { throw CalcError.message("invalid number") }
        return try checked(value)
    }
    func parse() throws -> Double { let value = try expression(); space(); if pos != input.count { throw CalcError.message("trailing input") }; return value }
}

do {
    guard CommandLine.arguments.count == 2 else { throw CalcError.message("expected exactly one expression") }
    let value = try Parser(CommandLine.arguments[1]).parse()
    print(String(format: "%.17g", locale: Locale(identifier: "en_US_POSIX"), value))
} catch {
    FileHandle.standardError.write(Data("error: \(error)\n".utf8))
    exit(1)
}
