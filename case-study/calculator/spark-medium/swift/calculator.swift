import Foundation

struct Parser {
    private let s: Array<Character>
    private var i: Int = 0
    private let n: Int

    init(_ expr: String) {
        self.s = Array(expr)
        self.n = s.count
    }

    mutating func parse() throws -> Double {
        let value = try parseExpr()
        skipWs()
        guard i == n else {
            throw ParseError.message("trailing tokens")
        }
        guard value.isFinite else {
            throw ParseError.message("non-finite result")
        }
        return value
    }

    private mutating func parseExpr() throws -> Double {
        return try parseAdd()
    }

    private mutating func parseAdd() throws -> Double {
        var value = try parseMul()
        while true {
            skipWs()
            if match("+") {
                let rhs = try parseMul()
                value += rhs
            } else if match("-") {
                let rhs = try parseMul()
                value -= rhs
            } else {
                break
            }
            guard value.isFinite else { throw ParseError.message("non-finite result") }
        }
        return value
    }

    private mutating func parseMul() throws -> Double {
        var value = try parseUnary()
        while true {
            skipWs()
            if match("*") {
                let rhs = try parseUnary()
                value *= rhs
            } else if match("/") {
                let rhs = try parseUnary()
                guard rhs != 0 else { throw ParseError.message("division by zero") }
                value /= rhs
            } else if match("%") {
                let rhs = try parseUnary()
                guard rhs != 0 else { throw ParseError.message("remainder by zero") }
                value = value.truncatingRemainder(dividingBy: rhs)
            } else {
                break
            }
            guard value.isFinite else { throw ParseError.message("non-finite result") }
        }
        return value
    }

    private mutating func parseUnary() throws -> Double {
        skipWs()
        if match("+") { return try parseUnary() }
        if match("-") {
            return try -parseUnary()
        }
        return try parsePow()
    }

    private mutating func parsePow() throws -> Double {
        let left = try parsePrimary()
        skipWs()
        if match("^") {
            let rhs = try parsePow()
            let value = pow(left, rhs)
            guard value.isFinite else { throw ParseError.message("non-finite result") }
            return value
        }
        return left
    }

    private mutating func parsePrimary() throws -> Double {
        skipWs()
        if match("(") {
            let value = try parseExpr()
            skipWs()
            guard match(")") else {
                throw ParseError.message("missing closing parenthesis")
            }
            skipWs()
            return value
        }
        return try parseNumber()
    }

    private mutating func parseNumber() throws -> Double {
        skipWs()
        let start = i
        var sawDigit = false
        var sawDot = false

        while i < n, s[i].isNumber {
            i += 1
            sawDigit = true
        }

        if i < n, s[i] == "." {
            sawDot = true
            i += 1
            while i < n, s[i].isNumber {
                i += 1
                sawDigit = true
            }
        }

        guard sawDigit || sawDot else {
            throw ParseError.message("expected number")
        }

        if i < n, s[i] == "e" || s[i] == "E" {
            i += 1
            if i < n, s[i] == "+" || s[i] == "-" {
                i += 1
            }
            guard i < n, s[i].isNumber else {
                throw ParseError.message("invalid exponent")
            }
            while i < n, s[i].isNumber { i += 1 }
        }

        let token = String(s[start..<i])
        guard let value = Double(token), value.isFinite else {
            throw ParseError.message("invalid number")
        }
        return value
    }

    private mutating func skipWs() {
        while i < n && s[i].isWhitespace {
            i += 1
        }
    }

    private mutating func match(_ ch: Character) -> Bool {
        if i < n && s[i] == ch {
            i += 1
            return true
        }
        return false
    }

    enum ParseError: Error {
        case message(String)
    }
}

func isNumericInput(_ args: [String]) -> Bool {
    return args.count == 2
}

if CommandLine.arguments.count != 2 {
    fputs("error: expected exactly one expression argument\n", stderr)
    exit(1)
}

var parser = Parser(CommandLine.arguments[1])
do {
    do {
        var value = try parser.parse()
        if value == -0.0 { value = 0.0 }
        print(String(format: "%.17g", value))
    } catch Parser.ParseError.message(let msg) {
        fputs("error: \(msg)\n", stderr)
        exit(1)
    } catch {
        fputs("error: parse failure\n", stderr)
        exit(1)
    }
}
