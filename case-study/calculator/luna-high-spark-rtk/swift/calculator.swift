import Foundation

func fail(_ message: String) -> Never {
    fputs("error: \(message)\n", stderr)
    exit(1)
}

final class Parser {
    private let input: ArraySlice<UInt8>
    private var index: Int = 0

    init(_ text: String) {
        input = Array(text.utf8)[...]
    }

    func parse() -> Double {
        let value = parseAddSub()
        skipWhitespace()
        if index != input.count {
            fail("trailing input")
        }
        return ensureFinite(value)
    }

    private func parseAddSub() -> Double {
        var value = parseMulDivMod()
        while true {
            skipWhitespace()
            if index >= input.count {
                break
            }
            let ch = input[input.startIndex + index]
            if ch == Character("+").asciiValue! {
                index += 1
                let right = parseMulDivMod()
                value = ensureFinite(value + right)
            } else if ch == Character("-").asciiValue! {
                index += 1
                let right = parseMulDivMod()
                value = ensureFinite(value - right)
            } else {
                break
            }
        }
        return value
    }

    private func parseMulDivMod() -> Double {
        var value = parseUnary()
        while true {
            skipWhitespace()
            if index >= input.count {
                break
            }
            let ch = input[input.startIndex + index]
            if ch == Character("*").asciiValue! {
                index += 1
                let right = parseUnary()
                value = ensureFinite(value * right)
            } else if ch == Character("/").asciiValue! {
                index += 1
                let right = parseUnary()
                if right == 0.0 {
                    fail("division by zero")
                }
                value = ensureFinite(value / right)
            } else if ch == Character("%").asciiValue! {
                index += 1
                let right = parseUnary()
                if right == 0.0 {
                    fail("remainder by zero")
                }
                value = ensureFinite(fmod(value, right))
            } else {
                break
            }
        }
        return value
    }

    private func parseUnary() -> Double {
        skipWhitespace()
        if index >= input.count {
            fail("malformed expression")
        }
        let ch = input[input.startIndex + index]
        if ch == Character("+").asciiValue! {
            index += 1
            return parseUnary()
        }
        if ch == Character("-").asciiValue! {
            index += 1
            return ensureFinite(-parseUnary())
        }
        return parsePow()
    }

    private func parsePow() -> Double {
        var value = parsePrimary()
        skipWhitespace()
        if index < input.count && input[input.startIndex + index] == Character("^").asciiValue! {
            index += 1
            let right = parsePow()
            value = ensureFinite(pow(value, right))
        }
        return value
    }

    private func parsePrimary() -> Double {
        skipWhitespace()
        if index >= input.count {
            fail("malformed expression")
        }
        let ch = input[input.startIndex + index]
        if ch == Character("(").asciiValue! {
            index += 1
            let value = parseAddSub()
            skipWhitespace()
            if index >= input.count || input[input.startIndex + index] != Character(")").asciiValue! {
                fail("missing closing parenthesis")
            }
            index += 1
            return value
        }
        return parseNumber()
    }

    private func parseNumber() -> Double {
        skipWhitespace()
        if index >= input.count {
            fail("malformed expression")
        }

        let start = index
        let startIndex = input.startIndex
        let first = input[startIndex + index]
        if !(first >= 48 && first <= 57) && first != 46 {
            fail("invalid token")
        }

        var hasDigits = false
        var sawDot = false

        if first == 46 {
            index += 1
        }

        while index < input.count {
            let byte = input[startIndex + index]
            if byte >= 48 && byte <= 57 {
                index += 1
                hasDigits = true
                continue
            }
            if byte == 46 && !sawDot {
                sawDot = true
                index += 1
                continue
            }
            if (byte == 69 || byte == 101) {
                if !hasDigits && !sawDot {
                    fail("invalid number")
                }
                index += 1
                if index < input.count && (input[startIndex + index] == 43 || input[startIndex + index] == 45) {
                    index += 1
                }
                let expStart = index
                while index < input.count {
                    let expByte = input[startIndex + index]
                    if expByte >= 48 && expByte <= 57 {
                        index += 1
                    } else {
                        break
                    }
                }
                if index == expStart {
                    fail("invalid number")
                }
                break
            }
            break
        }

        if index == start || (!hasDigits && !sawDot) {
            fail("invalid number")
        }

        let token = String(decoding: input[startIndex + start ..< (startIndex + index)], as: UTF8.self)
        guard let value = Double(token) else {
            fail("invalid number")
        }
        return ensureFinite(value)
    }

    private func skipWhitespace() {
        while index < input.count && ((input[input.startIndex + index] == 32) ||
                                     (input[input.startIndex + index] >= 9 && input[input.startIndex + index] <= 13)) {
            index += 1
        }
    }

    private func ensureFinite(_ value: Double) -> Double {
        if !value.isFinite {
            fail("non-finite result")
        }
        return value
    }
}

let args = CommandLine.arguments
if args.count != 2 {
    fail("expected exactly one argument")
}

let parser = Parser(args[1])
let result = parser.parse()
print(result)
