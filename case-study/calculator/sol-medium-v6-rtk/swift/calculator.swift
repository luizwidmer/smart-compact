import Foundation
enum CalcError: Error { case invalid }
func check(_ v: Double) throws -> Double { guard v.isFinite else { throw CalcError.invalid }; return v }
final class Parser {
    let s: [UInt8]; var p = 0
    init(_ text: String) { s = Array(text.utf8) }
    func space() { while p < s.count && [9,10,11,12,13,32].contains(s[p]) { p += 1 } }
    func take(_ c: UInt8) -> Bool { space(); if p < s.count && s[p] == c { p += 1; return true }; return false }
    func expression() throws -> Double { var v = try term(); while true { if take(43) { v = try check(v + term()) } else if take(45) { v = try check(v - term()) } else { return v } } }
    func term() throws -> Double { var v = try unary(); while true { if take(42) { v = try check(v * unary()) } else if take(47) { let r=try unary(); if r==0 { throw CalcError.invalid }; v=try check(v/r) } else if take(37) { let r=try unary(); if r==0 { throw CalcError.invalid }; v=try check(v.truncatingRemainder(dividingBy:r)) } else { return v } } }
    func unary() throws -> Double { if take(43) { return try unary() }; if take(45) { return try check(-unary()) }; return try power() }
    func power() throws -> Double { var v=try primary(); if take(94) { v=try check(Foundation.pow(v,unary())) }; return v }
    func primary() throws -> Double { if take(40) { let v=try expression(); if !take(41) { throw CalcError.invalid }; return v }; space(); let start=p; while p<s.count && s[p]>=48 && s[p]<=57 { p+=1 }; if p<s.count && s[p]==46 { p+=1; while p<s.count && s[p]>=48 && s[p]<=57 { p+=1 } }; if p==start || (p==start+1 && s[start]==46) { throw CalcError.invalid }; if p<s.count && (s[p]==101 || s[p]==69) { p+=1; if p<s.count && (s[p]==43 || s[p]==45) { p+=1 }; let e=p; while p<s.count && s[p]>=48 && s[p]<=57 { p+=1 }; if p==e { throw CalcError.invalid } }; guard let text=String(bytes:s[start..<p],encoding:.utf8),let v=Double(text) else { throw CalcError.invalid }; return try check(v) }
}
do { guard CommandLine.arguments.count == 2 else { throw CalcError.invalid }; let parser=Parser(CommandLine.arguments[1]); let v=try parser.expression(); parser.space(); guard parser.p==parser.s.count else { throw CalcError.invalid }; print(String(format:"%.17g",v)) } catch { FileHandle.standardError.write(Data("error: invalid expression\n".utf8)); exit(1) }
