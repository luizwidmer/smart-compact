#include <cmath>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>

double checked(double v) { if (!std::isfinite(v)) throw std::runtime_error("non-finite value or result"); return v; }
class Parser {
    std::string s; size_t p = 0;
    void skip() { while (p < s.size() && (s[p]==' '||s[p]=='\t'||s[p]=='\r'||s[p]=='\n'||s[p]=='\v'||s[p]=='\f')) ++p; }
    bool take(char c) { skip(); if (p < s.size() && s[p] == c) { ++p; return true; } return false; }
public:
    explicit Parser(std::string text): s(std::move(text)) {}
    double parse() { double v = additive(); skip(); if (p != s.size()) throw std::runtime_error("unexpected token"); return checked(v); }
private:
    double additive() { double v=multiplicative(); for (;;) { if(take('+')) v=checked(v+multiplicative()); else if(take('-')) v=checked(v-multiplicative()); else return v; } }
    double multiplicative() { double v=unary(); for (;;) { if(take('*')) v=checked(v*unary()); else if(take('/')) { double r=unary(); if(r==0) throw std::runtime_error("division by zero"); v=checked(v/r); } else if(take('%')) { double r=unary(); if(r==0) throw std::runtime_error("remainder by zero"); v=checked(std::fmod(v,r)); } else return v; } }
    double unary() { if(take('+')) return unary(); if(take('-')) return checked(-unary()); return power(); }
    double power() { double v=primary(); if(take('^')) v=checked(std::pow(v,unary())); return v; }
    double primary() {
        if(take('(')) { double v=additive(); if(!take(')')) throw std::runtime_error("expected closing parenthesis"); return v; }
        skip(); size_t start=p; bool digits=false; while(p<s.size()&&std::isdigit((unsigned char)s[p])) {++p;digits=true;} if(p<s.size()&&s[p]=='.'){++p;while(p<s.size()&&std::isdigit((unsigned char)s[p])){++p;digits=true;}} if(!digits) throw std::runtime_error("expected number");
        if(p<s.size()&&(s[p]=='e'||s[p]=='E')){++p;if(p<s.size()&&(s[p]=='+'||s[p]=='-'))++p;size_t e=p;while(p<s.size()&&std::isdigit((unsigned char)s[p]))++p;if(e==p)throw std::runtime_error("malformed exponent");}
        return checked(std::stod(s.substr(start,p-start)));
    }
};
int main(int argc,char**argv){try{if(argc!=2)throw std::runtime_error("expected exactly one expression");std::cout<<std::setprecision(17)<<Parser(argv[1]).parse()<<'\n';return 0;}catch(const std::exception&e){std::cerr<<"error: "<<e.what()<<'\n';return 1;}}
