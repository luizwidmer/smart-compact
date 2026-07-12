import Foundation

enum ParseError: Error {
    case message(String)
}

struct Parser {
    private let chars: [UInt8]
    private var pos: Int = 0

    init(_ input: String) {
        self.chars = Array(input.utf8)
    }

    mutating func parse() throws -> Double {
        let value = try parseExpr()
        skipWhitespace()
        if pos != chars.count {
            throw ParseError.message("trailing input")
        }
        return try ensureFinite(value)
    }

    private mutating func parseExpr() throws -> Double {
        var left = try parseTerm()
        while true {
            skipWhitespace()
            if match(ascii: 43) {
                let right = try parseTerm()
                left = try ensureFinite(left + right)
            } else if match(ascii: 45) {
                let right = try parseTerm()
                left = try ensureFinite(left - right)
            } else {
                return left
            }
        }
    }

    private mutating func parseTerm() throws -> Double {
        var left = try parsePow()
        while true {
            skipWhitespace()
            if match(ascii: 42) {
                let right = try parsePow()
                left = try ensureFinite(left * right)
            } else if match(ascii: 47) {
                let rhs = try parsePow()
                if rhs == 0.0 {
                    throw ParseError.message("division by zero")
                }
                left = try ensureFinite(left / rhs)
            } else if match(ascii: 37) {
                let rhs = try parsePow()
                if rhs == 0.0 {
                    throw ParseError.message("remainder by zero")
                }
                left = try ensureFinite(left.truncatingRemainder(dividingBy: rhs))
            } else {
                return left
            }
        }
    }

    private mutating func parsePow() throws -> Double {
        let left = try parseUnary()
        skipWhitespace()
        if match(ascii: 94) {
            let rhs = try parsePow()
            return try ensureFinite(pow(left, rhs))
        }
        return left
    }

    private mutating func parseUnary() throws -> Double {
        skipWhitespace()
        if match(ascii: 43) {
            return try parseUnary()
        }
        if match(ascii: 45) {
            let right = try parseUnary()
            return try ensureFinite(-right)
        }
        return try parsePrimary()
    }

    private mutating func parsePrimary() throws -> Double {
        skipWhitespace()
        if match(ascii: 40) {
            let value = try parseExpr()
            skipWhitespace()
            if !match(ascii: 41) {
                throw ParseError.message("missing ')'")
            }
            return value
        }

        guard pos < chars.count else {
            throw ParseError.message("unexpected end of input")
        }
        let ch = chars[pos]
        if ch == 46 || isDigit(ch) {
            return try parseNumber()
        }
        throw ParseError.message("unexpected token")
    }

    private mutating func parseNumber() throws -> Double {
        skipWhitespace()
        guard pos < chars.count else {
            throw ParseError.message("unexpected end of input")
        }

        let start = pos
        if chars[start] == 46 {
            if start + 1 >= chars.count || !isDigit(chars[start + 1]) {
                throw ParseError.message("invalid number")
            }
        } else if !isDigit(chars[start]) {
            throw ParseError.message("invalid number")
        }

        var idx = start
        while idx < chars.count && isDigit(chars[idx]) {
            idx += 1
        }
        if idx < chars.count && chars[idx] == 46 {
            idx += 1
            while idx < chars.count && isDigit(chars[idx]) {
                idx += 1
            }
        }
        if idx < chars.count && (chars[idx] == 101 || chars[idx] == 69) {
            idx += 1
            if idx < chars.count && (chars[idx] == 43 || chars[idx] == 45) {
                idx += 1
            }
            if idx >= chars.count || !isDigit(chars[idx]) {
                throw ParseError.message("invalid number")
            }
            while idx < chars.count && isDigit(chars[idx]) {
                idx += 1
            }
        }

        guard idx > start, let value = Double(String(decoding: chars[start..<idx], as: UTF8.self)) else {
            throw ParseError.message("invalid number")
        }
        pos = idx
        return try ensureFinite(value)
    }

    private mutating func skipWhitespace() {
        while pos < chars.count && isWhitespace(chars[pos]) {
            pos += 1
        }
    }

    private mutating func match(ascii: UInt8) -> Bool {
        if pos < chars.count && chars[pos] == ascii {
            pos += 1
            return true
        }
        return false
    }

    private mutating func ensureFinite(_ value: Double) throws -> Double {
        if !value.isFinite {
            throw ParseError.message("non-finite value")
        }
        return value
    }

    private func isDigit(_ ch: UInt8) -> Bool {
        return ch >= 48 && ch <= 57
    }

    private func isWhitespace(_ ch: UInt8) -> Bool {
        return ch == 9 || ch == 10 || ch == 13 || ch == 12 || ch == 11 || ch == 32
    }
}

func formatResult(_ value: Double) -> String {
    if value.truncatingRemainder(dividingBy: 1.0) == 0.0 {
        return String(format: "%.0f", value)
    }
    return String(format: "%.17g", value)
}

var args = CommandLine.arguments
if args.count != 2 {
    fputs("error: expected exactly one expression argument\n", stderr)
    exit(1)
}

var parser = Parser(args[1])
do {
    let value = try parser.parse()
    print(formatResult(value))
} catch ParseError.message(let message) {
    fputs("error: \(message)\n", stderr)
    exit(1)
} catch {
    fputs("error: parser failure\n", stderr)
    exit(1)
}
