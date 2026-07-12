import Foundation

enum CalcError: Error, CustomStringConvertible { case message(String); var description: String { if case .message(let s)=self{return s};return "error" } }
func checked(_ v: Double) throws -> Double { guard v.isFinite else { throw CalcError.message("non-finite value or result") }; return v }
final class Parser {
    let a:[UInt8]; var p=0
    init(_ s:String){a=Array(s.utf8)}
    func skip(){while p<a.count && [9,10,11,12,13,32].contains(a[p]){p+=1}}
    func take(_ c:UInt8)->Bool{skip();if p<a.count && a[p]==c{p+=1;return true};return false}
    func parse() throws -> Double {let v=try additive();skip();guard p==a.count else{throw CalcError.message("unexpected token")};return try checked(v)}
    func additive() throws -> Double {var v=try multiplicative();while true{if take(43){let r=try multiplicative();v=try checked(v+r)}else if take(45){let r=try multiplicative();v=try checked(v-r)}else{return v}}}
    func multiplicative() throws -> Double {var v=try unary();while true{if take(42){v=try checked(v*unary())}else if take(47){let r=try unary();guard r != 0 else{throw CalcError.message("division by zero")};v=try checked(v/r)}else if take(37){let r=try unary();guard r != 0 else{throw CalcError.message("remainder by zero")};v=try checked(v.truncatingRemainder(dividingBy:r))}else{return v}}}
    func unary() throws -> Double {if take(43){return try unary()};if take(45){return try checked(-unary())};return try power()}
    func power() throws -> Double {var v=try primary();if take(94){v=try checked(Foundation.pow(v,unary()))};return v}
    func primary() throws -> Double {if take(40){let v=try additive();guard take(41)else{throw CalcError.message("expected closing parenthesis")};return v};skip();let start=p;var digits=false;while p<a.count&&a[p]>=48&&a[p]<=57{p+=1;digits=true};if p<a.count&&a[p]==46{p+=1;while p<a.count&&a[p]>=48&&a[p]<=57{p+=1;digits=true}};guard digits else{throw CalcError.message("expected number")};if p<a.count&&(a[p]==101||a[p]==69){p+=1;if p<a.count&&(a[p]==43||a[p]==45){p+=1};let e=p;while p<a.count&&a[p]>=48&&a[p]<=57{p+=1};guard e != p else{throw CalcError.message("malformed exponent")}};guard let v=Double(String(decoding:a[start..<p],as:UTF8.self))else{throw CalcError.message("invalid number")};return try checked(v)}
}
do{guard CommandLine.arguments.count==2 else{throw CalcError.message("expected exactly one expression")};let v=try Parser(CommandLine.arguments[1]).parse();print(String(format:"%.17g",locale:Locale(identifier:"en_US_POSIX"),v))}catch{fputs("error: \(error)\n",stderr);exit(1)}
