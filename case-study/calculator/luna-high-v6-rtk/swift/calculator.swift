import Foundation

enum ParseError: Error {
    case message(String)
}

struct Parser {
    let text: [UInt8]
    var position = 0

    init(_ input: String) { text = Array(input.utf8) }

    mutating func skipSpace() {
        while position < text.count && [32, 9, 10, 13, 11, 12].contains(text[position]) { position += 1 }
    }
    mutating func take(_ wanted: UInt8) -> Bool {
        skipSpace()
        if position < text.count && text[position] == wanted { position += 1; return true }
        return false
    }
    func checked(_ value: Double) throws -> Double {
        guard value.isFinite else { throw ParseError.message("non-finite result") }
        return value
    }
    mutating func parse() throws -> Double {
        let value = try addition()
        skipSpace()
        guard position == text.count else { throw ParseError.message("trailing token") }
        return value
    }
    mutating func addition() throws -> Double {
        var value = try multiplication()
        while true {
            if take(43) { value = try checked(value + multiplication()) }
            else if take(45) { value = try checked(value - multiplication()) }
            else { return value }
        }
    }
    mutating func multiplication() throws -> Double {
        var value = try unary()
        while true {
            if take(42) { value = try checked(value * unary()) }
            else if take(47) {
                let right = try unary()
                if right == 0 { throw ParseError.message("division by zero") }
                value = try checked(value / right)
            } else if take(37) {
                let right = try unary()
                if right == 0 { throw ParseError.message("remainder by zero") }
                value = try checked(value.truncatingRemainder(dividingBy: right))
            } else { return value }
        }
    }
    mutating func unary() throws -> Double {
        if take(43) { return try unary() }
        if take(45) { return try checked(-unary()) }
        return try power()
    }
    mutating func power() throws -> Double {
        let value = try primary()
        if take(94) { return try checked(pow(value, unary())) }
        return value
    }
    mutating func primary() throws -> Double {
        if take(40) {
            let value = try addition()
            guard take(41) else { throw ParseError.message("missing closing parenthesis") }
            return value
        }
        skipSpace()
        let start = position
        var digits = 0
        while position < text.count && text[position] >= 48 && text[position] <= 57 { position += 1; digits += 1 }
        if position < text.count && text[position] == 46 {
            position += 1
            while position < text.count && text[position] >= 48 && text[position] <= 57 { position += 1 }
        } else if digits == 0 {
            throw ParseError.message("expected number or parenthesis")
        }
        if position < text.count && (text[position] == 101 || text[position] == 69) {
            position += 1
            if position < text.count && (text[position] == 43 || text[position] == 45) { position += 1 }
            let exponentStart = position
            while position < text.count && text[position] >= 48 && text[position] <= 57 { position += 1 }
            if exponentStart == position { throw ParseError.message("invalid exponent") }
        }
        let token = String(decoding: text[start..<position], as: UTF8.self)
        guard let value = Double(token) else { throw ParseError.message("invalid number") }
        return try checked(value)
    }
}

func main() -> Int32 {
    guard CommandLine.arguments.count == 2 else {
        FileHandle.standardError.write(Data("error: expected exactly one expression\n".utf8))
        return 2
    }
    do {
        var parser = Parser(CommandLine.arguments[1])
        let result = try parser.parse()
        print(String(format: "%.17g", result))
        return 0
    } catch let ParseError.message(message) {
        FileHandle.standardError.write(Data("error: \(message)\n".utf8))
        return 1
    } catch {
        FileHandle.standardError.write(Data("error: invalid expression\n".utf8))
        return 1
    }
}

exit(main())
