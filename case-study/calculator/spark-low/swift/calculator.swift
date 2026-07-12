import Foundation

struct ParseError: Error {
    let message: String
}

final class Parser {
    private let bytes: [UInt8]
    private var index: Int = 0

    init(_ input: String) {
        bytes = Array(input.utf8)
    }

    private var isDone: Bool { index >= bytes.count }

    private func isWs(_ b: UInt8) -> Bool {
        return b == 9 || b == 10 || b == 11 || b == 12 || b == 13 || b == 32
    }

    private func isDigit(_ b: UInt8) -> Bool {
        return b >= 48 && b <= 57
    }

    private func skipWs() {
        while !isDone && isWs(bytes[index]) { index += 1 }
    }

    private func token(from start: Int, _ end: Int) throws -> Double {
        let token = String(decoding: bytes[start..<end], as: UTF8.self)
        guard let value = Double(token), value.isFinite else {
            throw ParseError(message: "non-finite number")
        }
        return value
    }

    private func parseNumber() throws -> Double {
        skipWs()
        let start = index
        var hasDigit = false

        if !isDone && bytes[index] == 46 { // '.'
            index += 1
            while !isDone && isDigit(bytes[index]) { index += 1; hasDigit = true }
        } else {
            while !isDone && isDigit(bytes[index]) { index += 1; hasDigit = true }
            if !isDone && bytes[index] == 46 { // '.'
                index += 1
                while !isDone && isDigit(bytes[index]) { index += 1; hasDigit = true }
            }
        }

        if !hasDigit { throw ParseError(message: "invalid number") }

        if !isDone && (bytes[index] == 101 || bytes[index] == 69) { // eE
            index += 1
            if !isDone && (bytes[index] == 43 || bytes[index] == 45) { index += 1 }
            if isDone || !isDigit(bytes[index]) {
                throw ParseError(message: "invalid exponent")
            }
            while !isDone && isDigit(bytes[index]) { index += 1 }
        }

        return try token(from: start, index)
    }

    private func parsePrimary() throws -> Double {
        skipWs()
        if isDone { throw ParseError(message: "unexpected end") }

        if bytes[index] == 40 { // '('
            index += 1
            let value = try parseExpr()
            skipWs()
            guard !isDone && bytes[index] == 41 else { throw ParseError(message: "missing )") }
            index += 1
            return value
        }

        return try parseNumber()
    }

    private func parseUnary() throws -> Double {
        skipWs()
        if isDone { throw ParseError(message: "unexpected end") }
        if bytes[index] == 43 || bytes[index] == 45 {
            let op = bytes[index]
            index += 1
            let value = try parseUnary()
            return op == 45 ? -value : value
        }
        return try parsePrimary()
    }

    private func parsePower() throws -> Double {
        var value = try parseUnary()
        skipWs()
        if isDone || bytes[index] != 94 { return value }
        index += 1
        let right = try parsePower()
        value = pow(value, right)
        if !value.isFinite { throw ParseError(message: "non-finite result") }
        return value
    }

    private func parseTerm() throws -> Double {
        var value = try parsePower()
        while true {
            skipWs()
            if isDone { return value }
            let op = bytes[index]
            if op != 42 && op != 47 && op != 37 { return value }
            index += 1
            let rhs = try parsePower()
            switch op {
            case 42: value *= rhs
            case 47:
                if rhs == 0.0 { throw ParseError(message: "division by zero") }
                value /= rhs
            default: // '%'
                if rhs == 0.0 { throw ParseError(message: "remainder by zero") }
                value = value.truncatingRemainder(dividingBy: rhs)
            }
            if !value.isFinite { throw ParseError(message: "non-finite result") }
        }
    }

    private func parseExpr() throws -> Double {
        var value = try parseTerm()
        while true {
            skipWs()
            if isDone { return value }
            let op = bytes[index]
            if op != 43 && op != 45 { return value }
            index += 1
            let rhs = try parseTerm()
            value = (op == 43) ? value + rhs : value - rhs
        }
    }

    func parse() throws -> Double {
        skipWs()
        if isDone { throw ParseError(message: "empty expression") }
        let value = try parseExpr()
        skipWs()
        if !isDone { throw ParseError(message: "trailing token") }
        if !value.isFinite { throw ParseError(message: "non-finite result") }
        return value
    }
}

guard CommandLine.arguments.count == 2 else {
    fputs("error: expected exactly one expression\n", stderr)
    exit(1)
}

let parser = Parser(CommandLine.arguments[1])

do {
    let value = try parser.parse()
    print(String(value))
    exit(0)
} catch let err as ParseError {
    fputs("error: \(err.message)\n", stderr)
    exit(2)
} catch {
    fputs("error: unknown error\n", stderr)
    exit(2)
}
