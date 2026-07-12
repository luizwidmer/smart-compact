import Foundation

enum ParseError: Error {
    case message(String)
}

struct Parser {
    let source: [UInt8]
    var position = 0

    init(_ source: String) { self.source = Array(source.utf8) }

    mutating func skipSpace() {
        while position < source.count && source[position] <= 127 && CharacterSet.whitespacesAndNewlines.contains(UnicodeScalar(source[position])) { position += 1 }
    }

    mutating func take(_ character: UInt8) -> Bool {
        skipSpace()
        if position < source.count && source[position] == character { position += 1; return true }
        return false
    }

    mutating func parse() throws -> Double {
        let result = try parseAdditive()
        skipSpace()
        if position != source.count { throw ParseError.message("trailing tokens") }
        return result
    }

    mutating func parseAdditive() throws -> Double {
        var result = try parseMultiplicative()
        while true {
            if take(43) { result = try checked(result + parseMultiplicative()) }
            else if take(45) { result = try checked(result - parseMultiplicative()) }
            else { return result }
        }
    }

    mutating func parseMultiplicative() throws -> Double {
        var result = try parseUnary()
        while true {
            if take(42) { result = try checked(result * parseUnary()) }
            else if take(47) {
                let right = try parseUnary()
                if right == 0 { throw ParseError.message("division by zero") }
                result = try checked(result / right)
            } else if take(37) {
                let right = try parseUnary()
                if right == 0 { throw ParseError.message("remainder by zero") }
                result = try checked(result.truncatingRemainder(dividingBy: right))
            } else { return result }
        }
    }

    mutating func parseUnary() throws -> Double {
        if take(43) { return try parseUnary() }
        if take(45) { return try checked(-parseUnary()) }
        return try parsePower()
    }

    mutating func parsePower() throws -> Double {
        let result = try parsePrimary()
        if take(94) { return try checked(pow(result, try parseUnary())) }
        return result
    }

    mutating func parsePrimary() throws -> Double {
        if take(40) {
            let result = try parseAdditive()
            if !take(41) { throw ParseError.message("expected ')'") }
            return result
        }

        skipSpace()
        let start = position
        while position < source.count && source[position] >= 48 && source[position] <= 57 { position += 1 }
        if position < source.count && source[position] == 46 {
            position += 1
            while position < source.count && source[position] >= 48 && source[position] <= 57 { position += 1 }
        } else if start == position && position < source.count && source[position] == 46 {
            position += 1
            let fractionStart = position
            while position < source.count && source[position] >= 48 && source[position] <= 57 { position += 1 }
            if fractionStart == position { throw ParseError.message("expected number or '('") }
        }
        if start == position { throw ParseError.message("expected number or '('") }
        if position < source.count && (source[position] == 101 || source[position] == 69) {
            position += 1
            if position < source.count && (source[position] == 43 || source[position] == 45) { position += 1 }
            let exponentStart = position
            while position < source.count && source[position] >= 48 && source[position] <= 57 { position += 1 }
            if exponentStart == position { throw ParseError.message("invalid exponent") }
        }
        let text = String(decoding: source[start..<position], as: UTF8.self)
        guard let result = Double(text) else { throw ParseError.message("invalid number") }
        return try checked(result)
    }

    func checked(_ value: Double) throws -> Double {
        if value.isFinite { return value }
        throw ParseError.message("non-finite result")
    }
}

let arguments = CommandLine.arguments
if arguments.count != 2 {
    FileHandle.standardError.write(Data("error: expected exactly one expression\n".utf8))
    exit(1)
}
do {
    var parser = Parser(arguments[1])
    print(try parser.parse())
} catch ParseError.message(let message) {
    FileHandle.standardError.write(Data("error: \(message)\n".utf8))
    exit(1)
} catch {
    FileHandle.standardError.write(Data("error: calculator failure\n".utf8))
    exit(1)
}
