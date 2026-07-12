#include <cmath>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>

class Parser {
    std::string s; size_t p=0;
    void space(){ while(p<s.size() && (s[p]==' '||s[p]=='\t'||s[p]=='\n'||s[p]=='\r'||s[p]=='\f'||s[p]=='\v')) ++p; }
    bool take(char c){ space(); if(p<s.size()&&s[p]==c){++p;return true;} return false; }
    static double ok(double v){if(!std::isfinite(v))throw std::runtime_error("non-finite result");return v;}
    double add(){double v=mul();for(;;){if(take('+'))v=ok(v+mul());else if(take('-'))v=ok(v-mul());else return v;}}
    double mul(){double v=unary();for(;;){if(take('*'))v=ok(v*unary());else if(take('/')){double r=unary();if(r==0)throw std::runtime_error("division by zero");v=ok(v/r);}else if(take('%')){double r=unary();if(r==0)throw std::runtime_error("remainder by zero");v=ok(std::fmod(v,r));}else return v;}}
    double unary(){if(take('+'))return unary();if(take('-'))return ok(-unary());return power();}
    double power(){double v=primary();if(take('^'))v=ok(std::pow(v,unary()));return v;}
    double primary(){
        if(take('(')){double v=add();if(!take(')'))throw std::runtime_error("expected closing parenthesis");return v;}
        space();size_t start=p,n=0;while(p<s.size()&&s[p]>='0'&&s[p]<='9'){++p;++n;}if(p<s.size()&&s[p]=='.'){++p;while(p<s.size()&&s[p]>='0'&&s[p]<='9'){++p;++n;}}if(!n)throw std::runtime_error("expected number");
        if(p<s.size()&&(s[p]=='e'||s[p]=='E')){++p;if(p<s.size()&&(s[p]=='+'||s[p]=='-'))++p;size_t e=p;while(p<s.size()&&s[p]>='0'&&s[p]<='9')++p;if(e==p)throw std::runtime_error("malformed exponent");}
        try{return ok(std::stod(s.substr(start,p-start)));}catch(...){throw std::runtime_error("invalid number");}
    }
public: explicit Parser(std::string x):s(std::move(x)){} double parse(){double v=add();space();if(p!=s.size())throw std::runtime_error("unexpected token");return v;}
};
int main(int argc,char**argv){try{if(argc!=2)throw std::runtime_error("expected exactly one expression");std::cout<<std::setprecision(17)<<Parser(argv[1]).parse()<<'\n';return 0;}catch(const std::exception&e){std::cerr<<"error: "<<e.what()<<'\n';return 1;}}
