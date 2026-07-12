import Foundation

enum ParseError: Error {
  case parse(String)
}

final class Parser {
  private let chars: [UInt8]
  private let len: Int
  private var pos: Int = 0

  init(_ input: String) {
    chars = Array(input.utf8)
    len = chars.count
  }

  func parse() throws -> Double {
    skipWhitespace()
    if pos >= len {
      throw ParseError.parse("empty expression")
    }
    let value = try parseAddSub()
    skipWhitespace()
    if pos != len {
      throw ParseError.parse("unexpected token")
    }
    guard value.isFinite else {
      throw ParseError.parse("non-finite result")
    }
    return value
  }

  private func parseAddSub() throws -> Double {
    var value = try parseMulDiv()
    while true {
      skipWhitespace()
      if consume(ascii: 0x2B) {
        value += try parseMulDiv()
      } else if consume(ascii: 0x2D) {
        value -= try parseMulDiv()
      } else {
        break
      }
    }
    return value
  }

  private func parseMulDiv() throws -> Double {
    var value = try parseUnary()
    while true {
      skipWhitespace()
      if consume(ascii: 0x2A) {
        value *= try parseUnary()
      } else if consume(ascii: 0x2F) {
        let rhs = try parseUnary()
        if rhs == 0.0 {
          throw ParseError.parse("division by zero")
        }
        value /= rhs
      } else if consume(ascii: 0x25) {
        let rhs = try parseUnary()
        if rhs == 0.0 {
          throw ParseError.parse("remainder by zero")
        }
        value = value.truncatingRemainder(dividingBy: rhs)
      } else {
        break
      }
    }
    return value
  }

  private func parseUnary() throws -> Double {
    skipWhitespace()
    if consume(ascii: 0x2B) {
      return try parseUnary()
    }
    if consume(ascii: 0x2D) {
      return -(try parseUnary())
    }
    return try parsePow()
  }

  private func parsePow() throws -> Double {
    let left = try parsePrimary()
    skipWhitespace()
    if consume(ascii: 0x5E) {
      let right = try parsePow()
      return pow(left, right)
    }
    return left
  }

  private func parsePrimary() throws -> Double {
    skipWhitespace()
    if consume(ascii: 0x28) {
      let value = try parseAddSub()
      skipWhitespace()
      if !consume(ascii: 0x29) {
        throw ParseError.parse("missing closing parenthesis")
      }
      return value
    }
    return try parseNumber()
  }

  private func parseNumber() throws -> Double {
    let start = pos
    var sawDigitsBefore = false

    if match(ascii: 0x2E) {
      guard pos < len, isDigit(peek()) else {
        throw ParseError.parse("malformed number")
      }
      while pos < len && isDigit(peek()) {
        pos += 1
      }
    } else {
      while pos < len && isDigit(peek()) {
        sawDigitsBefore = true
        pos += 1
      }
      if match(ascii: 0x2E) {
        while pos < len && isDigit(peek()) {
          pos += 1
        }
      } else if !sawDigitsBefore {
        throw ParseError.parse("malformed number")
      }
    }

    if pos < len && (chars[pos] == 0x65 || chars[pos] == 0x45) {
      pos += 1
      if pos < len && (chars[pos] == 0x2B || chars[pos] == 0x2D) {
        pos += 1
      }
      guard pos < len, isDigit(peek()) else {
        throw ParseError.parse("malformed number")
      }
      while pos < len && isDigit(peek()) {
        pos += 1
      }
    }

    let data = Data(chars[start..<pos])
    guard
      let token = String(data: data, encoding: .utf8),
      let value = Double(token)
    else {
      throw ParseError.parse("malformed number")
    }
    if !value.isFinite {
      throw ParseError.parse("non-finite number")
    }
    return value
  }

  private func skipWhitespace() {
    while pos < len && isWhitespace(chars[pos]) {
      pos += 1
    }
  }

  private func consume(ascii value: UInt8) -> Bool {
    if pos < len && chars[pos] == value {
      pos += 1
      return true
    }
    return false
  }

  private func match(ascii value: UInt8) -> Bool {
    if chars.indices.contains(pos) && chars[pos] == value {
      pos += 1
      return true
    }
    return false
  }

  private func peek() -> UInt8 {
    return chars[pos]
  }

  private func isDigit(_ ch: UInt8) -> Bool {
    return ch >= 48 && ch <= 57
  }

  private func isWhitespace(_ ch: UInt8) -> Bool {
    switch ch {
    case 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x20:
      return true
    default:
      return false
    }
  }
}

func writeError(_ message: String) {
  if let data = ("error: " + message + "\n").data(using: .utf8) {
    FileHandle.standardError.write(data)
  }
}

let args = CommandLine.arguments
if args.count != 2 {
  writeError("expected one expression argument")
  exit(1)
}

do {
  let parser = Parser(args[1])
  let value = try parser.parse()
  let output = value == floor(value)
    ? String(format: "%.0f", value)
    : String(format: "%.17g", value)
  print(output)
  exit(0)
} catch ParseError.parse(let message) {
  writeError(message)
  exit(1)
}
