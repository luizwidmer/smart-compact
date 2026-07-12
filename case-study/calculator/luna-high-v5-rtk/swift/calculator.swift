import Foundation

enum CalcError: Error {
    case message(String)
}

struct Parser {
    let source: [UInt8]
    var pos = 0

    init(_ input: String) {
        source = Array(input.utf8)
    }

    static func checked(_ value: Double) throws -> Double {
        guard value.isFinite else { throw CalcError.message("non-finite result") }
        return value
    }

    mutating func skipSpace() {
        while pos < source.count && [32, 9, 10, 11, 12, 13].contains(source[pos]) { pos += 1 }
    }

    mutating func take(_ token: UInt8) -> Bool {
        skipSpace()
        guard pos < source.count, source[pos] == token else { return false }
        pos += 1
        return true
    }

    mutating func parse() throws -> Double {
        let value = try parseAdditive()
        skipSpace()
        if pos != source.count { throw CalcError.message("trailing tokens") }
        return value
    }

    mutating func parseAdditive() throws -> Double {
        var value = try parseMultiplicative()
        while true {
            if take(43) { value = try Self.checked(value + parseMultiplicative()) }
            else if take(45) { value = try Self.checked(value - parseMultiplicative()) }
            else { return value }
        }
    }

    mutating func parseMultiplicative() throws -> Double {
        var value = try parseUnary()
        while true {
            if take(42) { value = try Self.checked(value * parseUnary()) }
            else if take(47) {
                let rhs = try parseUnary()
                if rhs == 0 { throw CalcError.message("division by zero") }
                value = try Self.checked(value / rhs)
            } else if take(37) {
                let rhs = try parseUnary()
                if rhs == 0 { throw CalcError.message("remainder by zero") }
                value = try Self.checked(value.truncatingRemainder(dividingBy: rhs))
            } else { return value }
        }
    }

    mutating func parseUnary() throws -> Double {
        if take(43) { return try parseUnary() }
        if take(45) { return try Self.checked(-parseUnary()) }
        return try parsePower()
    }

    mutating func parsePower() throws -> Double {
        let value = try parsePrimary()
        if take(94) { return try Self.checked(pow(value, parseUnary())) }
        return value
    }

    mutating func parsePrimary() throws -> Double {
        skipSpace()
        if take(40) {
            let value = try parseAdditive()
            if !take(41) { throw CalcError.message("missing closing parenthesis") }
            return value
        }

        let start = pos
        var before = 0
        while pos < source.count && source[pos] >= 48 && source[pos] <= 57 { pos += 1; before += 1 }
        var after = 0
        if pos < source.count && source[pos] == 46 {
            pos += 1
            while pos < source.count && source[pos] >= 48 && source[pos] <= 57 { pos += 1; after += 1 }
        }
        if before == 0 && after == 0 { throw CalcError.message("expected number or parenthesis") }
        if pos < source.count && (source[pos] == 101 || source[pos] == 69) {
            pos += 1
            if pos < source.count && (source[pos] == 43 || source[pos] == 45) { pos += 1 }
            let exponentStart = pos
            while pos < source.count && source[pos] >= 48 && source[pos] <= 57 { pos += 1 }
            if pos == exponentStart { throw CalcError.message("invalid exponent") }
        }

        let token = String(decoding: source[start..<pos], as: UTF8.self)
        guard let value = Double(token) else { throw CalcError.message("invalid number") }
        return try Self.checked(value)
    }
}

let arguments = CommandLine.arguments
guard arguments.count == 2 else {
    fputs("error: expected exactly one expression\n", stderr)
    exit(1)
}
do {
    var parser = Parser(arguments[1])
    print(try parser.parse())
} catch let CalcError.message(message) {
    fputs("error: \(message)\n", stderr)
    exit(1)
} catch {
    fputs("error: calculator failure\n", stderr)
    exit(1)
}
