import Foundation

enum ParseError: Error {
    case msg(String)
}

final class Parser {
    private let input: [UInt8]
    private let n: Int
    private var pos: Int = 0

    init(_ text: String) {
        self.input = Array(text.utf8)
        self.n = self.input.count
    }

    func parse() throws -> Double {
        let value = try parseExpression()
        skipWS()
        if pos != n { throw ParseError.msg("unexpected trailing token") }
        return try ensureFinite(value)
    }

    private func ensureFinite(_ value: Double) throws -> Double {
        guard value.isFinite else {
            throw ParseError.msg("result is not finite")
        }
        return value
    }

    private func parseExpression() throws -> Double {
        var value = try parseTerm()
        while true {
            skipWS()
            if consume(UInt8(ascii: "+")) {
                let rhs = try parseTerm()
                value = try ensureFinite(value + rhs)
            } else if consume(UInt8(ascii: "-")) {
                let rhs = try parseTerm()
                value = try ensureFinite(value - rhs)
            } else {
                return value
            }
        }
    }

    private func parseTerm() throws -> Double {
        var value = try parsePower()
        while true {
            skipWS()
            if consume(UInt8(ascii: "*")) {
                let rhs = try parsePower()
                value = try ensureFinite(value * rhs)
            } else if consume(UInt8(ascii: "/")) {
                let rhs = try parsePower()
                if rhs == 0.0 { throw ParseError.msg("division by zero") }
                value = try ensureFinite(value / rhs)
            } else if consume(UInt8(ascii: "%")) {
                let rhs = try parsePower()
                if rhs == 0.0 { throw ParseError.msg("remainder by zero") }
                value = try ensureFinite(value.truncatingRemainder(dividingBy: rhs))
            } else {
                return value
            }
        }
    }

    private func parsePower() throws -> Double {
        let left = try parseUnary()
        skipWS()
        if consume(UInt8(ascii: "^")) {
            let right = try parsePower()
            return try ensureFinite(pow(left, right))
        }
        return left
    }

    private func parseUnary() throws -> Double {
        skipWS()
        if consume(UInt8(ascii: "+")) {
            return try parseUnary()
        }
        if consume(UInt8(ascii: "-")) {
            let value = try parseUnary()
            return try ensureFinite(-value)
        }
        return try parsePrimary()
    }

    private func parsePrimary() throws -> Double {
        skipWS()
        if consume(UInt8(ascii: "(")) {
            let value = try parseExpression()
            skipWS()
            if !consume(UInt8(ascii: ")")) {
                throw ParseError.msg("missing closing parenthesis")
            }
            return try ensureFinite(value)
        }
        return try parseNumber()
    }

    private func parseNumber() throws -> Double {
        skipWS()
        let start = pos

        if pos >= n {
            throw ParseError.msg("expected number")
        }

        if input[pos] == UInt8(ascii: ".") {
            pos += 1
            if pos >= n || !isDigit(input[pos]) {
                throw ParseError.msg("invalid number")
            }
            while pos < n && isDigit(input[pos]) {
                pos += 1
            }
        } else if isDigit(input[pos]) {
            while pos < n && isDigit(input[pos]) {
                pos += 1
            }
            if pos < n && input[pos] == UInt8(ascii: ".") {
                pos += 1
                while pos < n && isDigit(input[pos]) {
                    pos += 1
                }
            }
        } else {
            throw ParseError.msg("invalid number")
        }

        if pos < n && (input[pos] == UInt8(ascii: "e") || input[pos] == UInt8(ascii: "E")) {
            pos += 1
            if pos < n && (input[pos] == UInt8(ascii: "+") || input[pos] == UInt8(ascii: "-")) {
                pos += 1
            }
            if pos >= n || !isDigit(input[pos]) {
                throw ParseError.msg("invalid scientific notation")
            }
            while pos < n && isDigit(input[pos]) {
                pos += 1
            }
        }

        guard let token = String(bytes: input[start..<pos], encoding: .utf8),
              let value = Double(token) else {
            throw ParseError.msg("invalid number")
        }
        return try ensureFinite(value)
    }

    private func skipWS() {
        while pos < n && isWhitespace(input[pos]) {
            pos += 1
        }
    }

    private func consume(_ ch: UInt8) -> Bool {
        if pos < n && input[pos] == ch {
            pos += 1
            return true
        }
        return false
    }

    private func isDigit(_ ch: UInt8) -> Bool {
        return ch >= UInt8(ascii: "0") && ch <= UInt8(ascii: "9")
    }

    private func isWhitespace(_ ch: UInt8) -> Bool {
        return ch == 0x20 || ch == 0x09 || ch == 0x0A || ch == 0x0D || ch == 0x0B || ch == 0x0C
    }
}

extension UInt8 {
    init(ascii: String) {
        self = ascii.utf8.first!
    }
}

if CommandLine.arguments.count != 2 {
    fputs("error: expected one expression argument\n", stderr)
    exit(1)
}

let parser = Parser(CommandLine.arguments[1])
do {
    let value = try parser.parse()
    print(value)
} catch ParseError.msg(let message) {
    fputs("error: \(message)\n", stderr)
    exit(1)
} catch {
    fputs("error: parse error\n", stderr)
    exit(1)
}
