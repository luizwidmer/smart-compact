import Foundation

func error(_ msg: String) -> Never {
    fputs("error: \(msg)\n", stderr)
    exit(1)
}

final class Lexer {
    let text: [UInt8]
    var i: Int = 0
    let n: Int

    init(_ s: String) {
        self.text = Array(s.utf8)
        self.n = text.count
    }

    func isWs(_ b: UInt8) -> Bool { b == 0x20 || b == 0x09 || b == 0x0A || b == 0x0D }

    func skipWs() {
        while i < n && isWs(text[i]) { i += 1 }
    }

    func parse() -> Double {
        let v = parseExpr()
        skipWs()
        if i != n { error("unexpected token") }
        if !v.isFinite { error("non-finite result") }
        return v
    }

    func parseExpr() -> Double {
        var v = parseTerm()
        while true {
            skipWs()
            if i >= n { break }
            let c = text[i]
            if c != 43 && c != 45 { break } // + -
            i += 1
            let rhs = parseTerm()
            if c == 43 { v += rhs } else { v -= rhs }
            if !v.isFinite { error("non-finite result") }
        }
        return v
    }

    func parseTerm() -> Double {
        var v = parseUnary()
        while true {
            skipWs()
            if i >= n { break }
            let c = text[i]
            if c != 42 && c != 47 && c != 37 { break } // * / %
            i += 1
            let rhs = parseUnary()
            if c == 42 {
                v *= rhs
            } else if c == 47 {
                if rhs == 0 { error("division by zero") }
                v /= rhs
            } else {
                if rhs == 0 { error("remainder by zero") }
                v = v.truncatingRemainder(dividingBy: rhs)
            }
            if !v.isFinite { error("non-finite result") }
        }
        return v
    }

    func parseUnary() -> Double {
        skipWs()
        if i >= n { error("unexpected end of input") }
        let c = text[i]
        if c == 43 { i += 1; return parseUnary() }
        if c == 45 { i += 1; return -parseUnary() }
        return parsePower()
    }

    func parsePower() -> Double {
        var v = parsePrimary()
        skipWs()
        if i < n && text[i] == 94 { // ^
            i += 1
            let rhs = parseUnary()
            v = pow(v, rhs)
            if !v.isFinite { error("non-finite result") }
        }
        return v
    }

    func parseNumber() -> Double? {
        skipWs()
        let start = i
        if start >= n { return nil }

        var hasDigit = false

        if text[i] == 46 { // '.'
            i += 1
            if i < n && text[i] >= 48 && text[i] <= 57 {
                hasDigit = true
                while i < n && text[i] >= 48 && text[i] <= 57 { i += 1 }
            } else {
                return nil
            }
        } else if text[i] >= 48 && text[i] <= 57 {
            while i < n && text[i] >= 48 && text[i] <= 57 { i += 1; hasDigit = true }
            if i < n && text[i] == 46 {
                i += 1
                while i < n && text[i] >= 48 && text[i] <= 57 { i += 1 }
            }
        } else {
            return nil
        }

        if i < n && (text[i] == 101 || text[i] == 69) {
            i += 1
            if i < n && (text[i] == 43 || text[i] == 45) { i += 1 }
            if i >= n || text[i] < 48 || text[i] > 57 { return nil }
            while i < n && text[i] >= 48 && text[i] <= 57 { i += 1 }
        }

        if !hasDigit { return nil }

        let token = String(decoding: text[start..<i], as: UTF8.self)
        return Double(token)
    }

    func parsePrimary() -> Double {
        skipWs()
        if i >= n { error("unexpected end of input") }
        if text[i] == 40 { // (
            i += 1
            let v = parseExpr()
            skipWs()
            if i >= n || text[i] != 41 { error("missing closing parenthesis") }
            i += 1
            return v
        }
        guard let v = parseNumber() else { error("invalid number") }
        return v
    }
}

let argv = CommandLine.arguments
if argv.count != 2 { error("usage: calculator <expression>") }
let p = Lexer(argv[1])
let v = p.parse()
if !v.isFinite { error("non-finite result") }
if v == Double(Int64(v)) {
    print(Int64(v))
} else {
    print(String(format: "%.17g", v))
}
