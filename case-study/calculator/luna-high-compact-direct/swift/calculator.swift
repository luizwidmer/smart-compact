import Foundation

enum ParseError: Error { case invalid }

struct Parser {
    let input: [Character]
    var position = 0

    init(_ text: String) { input = Array(text) }

    mutating func skipSpace() {
        while position < input.count && " \t\n\r\u{0B}\u{0C}".contains(input[position]) { position += 1 }
    }

    mutating func take(_ token: Character) -> Bool {
        skipSpace()
        guard position < input.count, input[position] == token else { return false }
        position += 1
        return true
    }

    mutating func expression() throws -> Double {
        var value = try term()
        while true {
            if take("+") { value = try checked(value + term()) }
            else if take("-") { value = try checked(value - term()) }
            else { return value }
        }
    }

    mutating func term() throws -> Double {
        var value = try unary()
        while true {
            if take("*") { value = try checked(value * unary()) }
            else if take("/") {
                let right = try unary()
                if right == 0 { throw ParseError.invalid }
                value = try checked(value / right)
            } else if take("%") {
                let right = try unary()
                if right == 0 { throw ParseError.invalid }
                value = try checked(value.truncatingRemainder(dividingBy: right))
            } else { return value }
        }
    }

    mutating func unary() throws -> Double {
        if take("+") { return try unary() }
        if take("-") { return try checked(-unary()) }
        return try power()
    }

    mutating func power() throws -> Double {
        let value = try primary()
        if take("^") { return try checked(pow(value, try unary())) }
        return value
    }

    mutating func primary() throws -> Double {
        if take("(") {
            let value = try expression()
            guard take(")") else { throw ParseError.invalid }
            return value
        }

        skipSpace()
        let start = position
        while position < input.count && input[position].isNumber { position += 1 }
        if position < input.count && input[position] == "." {
            position += 1
            while position < input.count && input[position].isNumber { position += 1 }
        } else if position == start && position < input.count && input[position] == "." {
            position += 1
            let fractionStart = position
            while position < input.count && input[position].isNumber { position += 1 }
            if position == fractionStart { throw ParseError.invalid }
        }
        guard position > start else { throw ParseError.invalid }
        if position < input.count && (input[position] == "e" || input[position] == "E") {
            position += 1
            if position < input.count && (input[position] == "+" || input[position] == "-") { position += 1 }
            let exponentStart = position
            while position < input.count && input[position].isNumber { position += 1 }
            if position == exponentStart { throw ParseError.invalid }
        }
        let token = String(input[start..<position])
        guard let value = Double(token) else { throw ParseError.invalid }
        return try checked(value)
    }

    func checked(_ value: Double) throws -> Double {
        guard value.isFinite else { throw ParseError.invalid }
        return value
    }

    mutating func parse() throws -> Double {
        let value = try expression()
        skipSpace()
        guard position == input.count else { throw ParseError.invalid }
        return try checked(value)
    }
}

let arguments = CommandLine.arguments
guard arguments.count == 2 else {
    FileHandle.standardError.write(Data("error: expected exactly one expression argument\n".utf8))
    exit(2)
}

do {
    var parser = Parser(arguments[1])
    let result = try parser.parse()
    print(String(format: "%.17g", locale: Locale(identifier: "en_US_POSIX"), result))
} catch {
    FileHandle.standardError.write(Data("error: invalid expression\n".utf8))
    exit(1)
}
