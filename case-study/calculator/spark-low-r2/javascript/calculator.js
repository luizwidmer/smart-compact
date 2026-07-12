#!/usr/bin/env node
'use strict'

function fail(msg) {
  console.error(`error: ${msg}`)
  process.exit(1)
}

class Parser {
  constructor(text) {
    this.text = text
    this.i = 0
    this.n = text.length
  }

  skipWs() {
    while (this.i < this.n && /\s/.test(this.text[this.i])) this.i++
  }

  parse() {
    const v = this.parseExpr()
    this.skipWs()
    if (this.i !== this.n) fail('unexpected token')
    if (!Number.isFinite(v)) fail('non-finite result')
    return v
  }

  parseExpr() {
    let v = this.parseTerm()
    while (true) {
      this.skipWs()
      if (this.i >= this.n) break
      const op = this.text[this.i]
      if (op !== '+' && op !== '-') break
      this.i++
      const rhs = this.parseTerm()
      v = op === '+' ? v + rhs : v - rhs
      if (!Number.isFinite(v)) fail('non-finite result')
    }
    return v
  }

  parseTerm() {
    let v = this.parseUnary()
    while (true) {
      this.skipWs()
      if (this.i >= this.n) break
      const op = this.text[this.i]
      if (op !== '*' && op !== '/' && op !== '%') break
      this.i++
      const rhs = this.parseUnary()
      if (op === '*') {
        v *= rhs
      } else if (op === '/') {
        if (rhs === 0) fail('division by zero')
        v /= rhs
      } else {
        if (rhs === 0) fail('remainder by zero')
        v = v % rhs
      }
      if (!Number.isFinite(v)) fail('non-finite result')
    }
    return v
  }

  parseUnary() {
    this.skipWs()
    if (this.i >= this.n) fail('unexpected end of input')
    if (this.text[this.i] === '+') {
      this.i++
      return this.parseUnary()
    }
    if (this.text[this.i] === '-') {
      this.i++
      return -this.parseUnary()
    }
    return this.parsePower()
  }

  parsePower() {
    let v = this.parsePrimary()
    this.skipWs()
    if (this.i < this.n && this.text[this.i] === '^') {
      this.i++
      const rhs = this.parseUnary()
      v = v ** rhs
      if (!Number.isFinite(v)) fail('non-finite result')
    }
    return v
  }

  parseNumber() {
    const start = this.i
    if (start >= this.n) return null

    let j = start
    if (this.text[j] === '+ ' || this.text[j] === '-') return null

    let hasDigit = false
    if (this.text[j] === '.') {
      j++
      if (j < this.n && this.text[j] >= '0' && this.text[j] <= '9') {
        hasDigit = true
        while (j < this.n && this.text[j] >= '0' && this.text[j] <= '9') j++
      } else {
        return null
      }
    } else if (this.text[j] >= '0' && this.text[j] <= '9') {
      while (j < this.n && this.text[j] >= '0' && this.text[j] <= '9') {
        j++
        hasDigit = true
      }
      if (this.text[j] === '.') {
        j++
        while (j < this.n && this.text[j] >= '0' && this.text[j] <= '9') j++
      }
    } else {
      return null
    }

    if (this.text[j] === 'e' || this.text[j] === 'E') {
      j++
      if (this.text[j] === '+' || this.text[j] === '-') j++
      if (j >= this.n || this.text[j] < '0' || this.text[j] > '9') return null
      while (j < this.n && this.text[j] >= '0' && this.text[j] <= '9') j++
    }

    if (!hasDigit) return null
    const token = this.text.slice(start, j)
    const value = Number(token)
    if (!Number.isFinite(value)) return null
    this.i = j
    return value
  }

  parsePrimary() {
    this.skipWs()
    if (this.i >= this.n) fail('unexpected end of input')
    if (this.text[this.i] === '(') {
      this.i++
      const v = this.parseExpr()
      this.skipWs()
      if (this.i >= this.n || this.text[this.i] !== ')') fail('missing closing parenthesis')
      this.i++
      return v
    }
    const v = this.parseNumber()
    if (v === null) fail('invalid number')
    return v
  }
}

if (process.argv.length !== 3) fail('usage: calculator <expression>')
const parser = new Parser(process.argv[2])
const value = parser.parse()
if (!Number.isFinite(value)) fail('non-finite result')
if (Number.isInteger(value)) {
  console.log(Math.trunc(value).toString())
} else {
  console.log(String(value))
}
