import Foundation

enum CalcError: Error { case message(String) }
func finite(_ v: Double) throws -> Double { if !v.isFinite { throw CalcError.message("non-finite result") }; return v }

final class Parser {
    let a: [UInt8]; var p = 0
    init(_ s: String) { a = Array(s.utf8) }
    func space() { while p < a.count && [32,9,10,13,12,11].contains(a[p]) { p += 1 } }
    func take(_ c: UInt8) -> Bool { space(); if p < a.count && a[p] == c { p += 1; return true }; return false }
    func parse() throws -> Double { let v = try add(); space(); if p != a.count { throw CalcError.message("unexpected token") }; return v }
    func add() throws -> Double { var v=try mul(); while true { if take(43) { v=try finite(v + mul()) } else if take(45) { v=try finite(v - mul()) } else { return v } } }
    func mul() throws -> Double { var v=try unary(); while true { if take(42) { v=try finite(v * unary()) } else if take(47) { let r=try unary();if r == 0 {throw CalcError.message("division by zero")};v=try finite(v/r) } else if take(37) {let r=try unary();if r == 0 {throw CalcError.message("remainder by zero")};v=try finite(v.truncatingRemainder(dividingBy:r))} else{return v} } }
    func unary() throws -> Double { if take(43){return try unary()};if take(45){return try finite(-unary())};return try power() }
    func power() throws -> Double { var v=try primary();if take(94){v=try finite(Foundation.pow(v,unary()))};return v }
    func primary() throws -> Double {
        if take(40){let v=try add();if !take(41){throw CalcError.message("expected closing parenthesis")};return v}
        space();let start=p;var n=0;while p<a.count && a[p]>=48 && a[p]<=57{p+=1;n+=1};if p<a.count && a[p]==46{p+=1;while p<a.count && a[p]>=48 && a[p]<=57{p+=1;n+=1}};if n==0{throw CalcError.message("expected number")}
        if p<a.count && (a[p]==101 || a[p]==69){p+=1;if p<a.count && (a[p]==43 || a[p]==45){p+=1};let e=p;while p<a.count && a[p]>=48 && a[p]<=57{p+=1};if e==p{throw CalcError.message("malformed exponent")}}
        guard let text=String(bytes:a[start..<p],encoding:.utf8),let v=Double(text) else{throw CalcError.message("invalid number")};return try finite(v)
    }
}
do { if CommandLine.arguments.count != 2 {throw CalcError.message("expected exactly one expression")};print(try Parser(CommandLine.arguments[1]).parse()) } catch CalcError.message(let m) { fputs("error: \(m)\n",stderr);exit(1) } catch { fputs("error: calculation failed\n",stderr);exit(1) }
