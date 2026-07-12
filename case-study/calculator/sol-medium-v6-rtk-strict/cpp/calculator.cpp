#include <cmath>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
using namespace std;
struct P{string s;size_t i=0;P(string x):s(x){}void ws(){while(i<s.size()&&(s[i]==' '||s[i]=='\t'||s[i]=='\n'||s[i]=='\r'||s[i]=='\f'||s[i]=='\v'))i++;}bool eat(char c){ws();if(i<s.size()&&s[i]==c){i++;return true;}return false;}double ck(double v){if(!isfinite(v))throw runtime_error("non-finite value");return v;}double num(){ws();const char*b=s.c_str()+i,*e=b;char*end;double v=strtod(b,&end);if(end==b)throw runtime_error("expected number");i+=end-b;return ck(v);}double prim(){if(eat('(')){double v=add();if(!eat(')'))throw runtime_error("expected ')'");return v;}return num();}double power(){double v=prim();if(eat('^'))v=pow(v,unary());return ck(v);}double unary(){if(eat('+'))return ck(unary());if(eat('-'))return ck(-unary());return power();}double mul(){double v=unary();for(;;){if(eat('*'))v*=unary();else if(eat('/')){double r=unary();if(r==0)throw runtime_error("division by zero");v/=r;}else if(eat('%')){double r=unary();if(r==0)throw runtime_error("remainder by zero");v=fmod(v,r);}else return v;v=ck(v);}}double add(){double v=mul();for(;;){if(eat('+'))v+=mul();else if(eat('-'))v-=mul();else return v;v=ck(v);}}double parse(){double v=add();ws();if(i!=s.size())throw runtime_error("trailing token");return v;}};
int main(int n,char**a){try{if(n!=2)throw runtime_error("expected one expression");cout<<setprecision(17)<<P(a[1]).parse()<<'\n';return 0;}catch(const exception&e){cerr<<"error: "<<e.what()<<'\n';return 1;}}
