import Foundation

#if os(Linux)
import Glibc
#else
import Darwin
#endif

struct Parser {
    let text: [UInt8]
    var pos = 0

    init(_ input: String) { text = Array(input.utf8) }

    static func isSpace(_ byte: UInt8) -> Bool {
        byte == 32 || byte == 9 || byte == 10 || byte == 11 || byte == 12 || byte == 13
    }

    mutating func skipSpace() {
        while pos < text.count && Self.isSpace(text[pos]) { pos += 1 }
    }

    func checked(_ value: Double) throws -> Double {
        guard value.isFinite else { throw CalcError("non-finite result") }
        return value
    }

    mutating func parse() throws -> Double {
        let value = try parseAdditive()
        skipSpace()
        guard pos == text.count else { throw CalcError("trailing tokens") }
        return try checked(value)
    }

    mutating func parseAdditive() throws -> Double {
        var value = try parseMultiplicative()
        while true {
            skipSpace()
            guard pos < text.count, text[pos] == 43 || text[pos] == 45 else { return value }
            let op = text[pos]
            pos += 1
            let right = try parseMultiplicative()
            value = try checked(op == 43 ? value + right : value - right)
        }
    }

    mutating func parseMultiplicative() throws -> Double {
        var value = try parseUnary()
        while true {
            skipSpace()
            guard pos < text.count, text[pos] == 42 || text[pos] == 47 || text[pos] == 37 else { return value }
            let op = text[pos]
            pos += 1
            let right = try parseUnary()
            guard right != 0 else { throw CalcError("division by zero") }
            if op == 42 { value = try checked(value * right) }
            else if op == 47 { value = try checked(value / right) }
            else { value = try checked(value.truncatingRemainder(dividingBy: right)) }
        }
    }

    mutating func parseUnary() throws -> Double {
        skipSpace()
        if pos < text.count, text[pos] == 43 || text[pos] == 45 {
            let op = text[pos]
            pos += 1
            let value = try parseUnary()
            return try checked(op == 43 ? value : -value)
        }
        return try parsePower()
    }

    mutating func parsePower() throws -> Double {
        let value = try parsePrimary()
        skipSpace()
        if pos < text.count, text[pos] == 94 {
            pos += 1
            return try checked(pow(value, try parseUnary()))
        }
        return value
    }

    mutating func parsePrimary() throws -> Double {
        skipSpace()
        guard pos < text.count else { throw CalcError("expected expression") }
        if text[pos] == 40 {
            pos += 1
            let value = try parseAdditive()
            skipSpace()
            guard pos < text.count, text[pos] == 41 else { throw CalcError("expected closing parenthesis") }
            pos += 1
            return value
        }
        return try parseNumber()
    }

    mutating func parseNumber() throws -> Double {
        let start = pos
        var digits = 0
        while pos < text.count, text[pos] >= 48, text[pos] <= 57 { pos += 1; digits += 1 }
        if pos < text.count, text[pos] == 46 {
            pos += 1
            while pos < text.count, text[pos] >= 48, text[pos] <= 57 { pos += 1; digits += 1 }
        }
        guard digits > 0 else { throw CalcError("expected number") }
        if pos < text.count, text[pos] == 101 || text[pos] == 69 {
            pos += 1
            if pos < text.count, text[pos] == 43 || text[pos] == 45 { pos += 1 }
            let exponentStart = pos
            while pos < text.count, text[pos] >= 48, text[pos] <= 57 { pos += 1 }
            guard pos != exponentStart else { throw CalcError("invalid exponent") }
        }
        let token = String(decoding: text[start..<pos], as: UTF8.self)
        guard let value = Double(token) else { throw CalcError("invalid number") }
        return try checked(value)
    }
}

struct CalcError: Error {
    let message: String
    init(_ message: String) { self.message = message }
}

func run() -> Int32 {
    guard CommandLine.arguments.count == 2 else {
        FileHandle.standardError.write(Data("error: expected exactly one argument\n".utf8))
        return 1
    }
    do {
        var parser = Parser(CommandLine.arguments[1])
        let result = try parser.parse()
        print(String(result))
        return 0
    } catch let error as CalcError {
        FileHandle.standardError.write(Data("error: \(error.message)\n".utf8))
        return 1
    } catch {
        FileHandle.standardError.write(Data("error: invalid expression\n".utf8))
        return 1
    }
}

exit(run())
