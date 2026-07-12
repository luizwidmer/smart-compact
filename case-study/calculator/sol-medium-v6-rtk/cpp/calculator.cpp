#include <cmath>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
using std::string;
double check(double v){if(!std::isfinite(v)) throw std::runtime_error("bad"); return v;}
struct Parser {
  string s; size_t p=0;
  void space(){while(p<s.size() && (s[p]==' '||s[p]=='\t'||s[p]=='\n'||s[p]=='\r'||s[p]=='\v'||s[p]=='\f')) ++p;}
  bool take(char c){space(); if(p<s.size()&&s[p]==c){++p;return true;}return false;}
  double expression(){double v=term();for(;;){if(take('+'))v=check(v+term());else if(take('-'))v=check(v-term());else return v;}}
  double term(){double v=unary();for(;;){if(take('*'))v=check(v*unary());else if(take('/')){double r=unary();if(r==0)throw std::runtime_error("zero");v=check(v/r);}else if(take('%')){double r=unary();if(r==0)throw std::runtime_error("zero");v=check(std::fmod(v,r));}else return v;}}
  double unary(){if(take('+'))return unary();if(take('-'))return check(-unary());return power();}
  double power(){double v=primary();if(take('^'))v=check(std::pow(v,unary()));return v;}
  double primary(){if(take('(')){double v=expression();if(!take(')'))throw std::runtime_error("paren");return v;}space();const char* start=s.c_str()+p;char* end=nullptr;double v=std::strtod(start,&end);if(end==start)throw std::runtime_error("number");p+=size_t(end-start);return check(v);}
};
int main(int argc,char**argv){try{if(argc!=2)throw std::runtime_error("args");Parser p{argv[1]};double v=p.expression();p.space();if(p.p!=p.s.size())throw std::runtime_error("trailing");std::cout<<std::setprecision(17)<<v<<'\n';return 0;}catch(...){std::cerr<<"error: invalid expression\n";return 1;}}
