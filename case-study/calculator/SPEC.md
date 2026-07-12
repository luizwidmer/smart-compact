# Cross-language calculator contract

Implement the same command-line expression calculator in six languages inside the assigned workspace. Do not use `eval`, subprocess delegation to another implementation, external packages, generated parsers, or network access.

## Required files

- `python/calculator.py`
- `rust/calculator.rs`
- `cpp/calculator.cpp`
- `swift/calculator.swift`
- `javascript/calculator.js`
- `typescript/calculator.ts`

Each file must contain an independent implementation in its own language.

## Command-line interface

- Accept exactly one argument containing the complete expression.
- On success, print only the numeric result followed by a newline and exit `0`.
- Output enough significant digits for a binary `float64` result to round-trip. Integer-valued results may be printed without a decimal suffix.
- On any error, print one line beginning with `error:` to standard error and exit nonzero.
- Missing or extra arguments are errors.

## Grammar and semantics

Support:

- decimal numbers, including `12`, `12.5`, `.5`, and scientific notation such as `1e3` and `2.5e-2`;
- arbitrary ASCII whitespace between tokens;
- parentheses;
- binary `+`, `-`, `*`, `/`, `%`, and `^`;
- unary `+` and `-`;
- precedence from lowest to highest: addition/subtraction, multiplication/division/remainder, unary signs, exponentiation;
- right-associative exponentiation, so `2^3^2` is `512`;
- finite IEEE-754 double-precision arithmetic.

Reject malformed syntax, trailing tokens, division or remainder by zero, and non-finite inputs or results. Remainder follows the host language floating-point remainder operation; benchmark cases avoid sign ambiguity.

## Toolchain commands used by validation

- Python: `python3 python/calculator.py EXPR`
- Rust: `rustc -O rust/calculator.rs -o BUILD/calculator-rust`
- C++: `g++ -std=c++17 -O2 cpp/calculator.cpp -o BUILD/calculator-cpp`
- Swift: `swiftc -O swift/calculator.swift -o BUILD/calculator-swift`
- JavaScript: `node javascript/calculator.js EXPR`
- TypeScript: `node typescript/calculator.ts EXPR` using the installed Node runtime's native type stripping.

## Completion

Compile every compiled implementation, run representative smoke tests in all six languages, and report changed files, validation performed, and material residual risks. Do not modify files outside the assigned workspace.
