#!/usr/bin/env python3
"""Compile and black-box test every calculator benchmark arm."""

from __future__ import annotations

import argparse
import json
import math
import subprocess
from pathlib import Path


VALID_CASES = [
    ("0", 0.0),
    ("2+3", 5.0),
    ("1+2*3", 7.0),
    ("(1+2)*3", 9.0),
    ("-5+2", -3.0),
    ("--5", 5.0),
    ("+(-3)", -3.0),
    ("2^3^2", 512.0),
    ("(2^3)^2", 64.0),
    ("10/4", 2.5),
    ("10%4", 2.0),
    ("9%2.5", 1.5),
    ("5.5*2", 11.0),
    (".5+.25", 0.75),
    ("3+-2", 1.0),
    ("2*-3", -6.0),
    ("-(2+3)*4", -20.0),
    ("1e3 + 2.5e-2", 1000.025),
    (" 7 +\t8\n", 15.0),
    ("0.1+0.2", 0.3),
    ("123456789*9", 1111111101.0),
    ("20/5/2", 2.0),
    ("20-(5-2)", 17.0),
    ("2^0", 1.0),
]

INVALID_CASES = [
    "",
    "1+",
    "(1+2",
    "1+2)",
    "1/0",
    "5%0",
    "2**3",
    "abc",
    "1 2",
    ")1(",
    ".",
    "1e",
    "1e309",
    "0^-1",
]

ARMS = (
    "standard-rtk",
    "smart-compact-rtk",
    "standard-direct",
    "smart-compact-direct",
)


def run(command: list[str], *, cwd: Path, timeout: int = 20) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def compile_commands(arm: Path, build: Path) -> dict[str, list[str]]:
    return {
        "rust": ["rustc", "-O", str(arm / "rust/calculator.rs"), "-o", str(build / "calculator-rust")],
        "cpp": ["g++", "-std=c++17", "-O2", str(arm / "cpp/calculator.cpp"), "-o", str(build / "calculator-cpp")],
        "swift": ["swiftc", "-O", str(arm / "swift/calculator.swift"), "-o", str(build / "calculator-swift")],
    }


def runtime_commands(arm: Path, build: Path) -> dict[str, list[str]]:
    return {
        "python": ["python3", str(arm / "python/calculator.py")],
        "rust": [str(build / "calculator-rust")],
        "cpp": [str(build / "calculator-cpp")],
        "swift": [str(build / "calculator-swift")],
        "javascript": ["node", str(arm / "javascript/calculator.js")],
        "typescript": ["node", str(arm / "typescript/calculator.ts")],
    }


def test_language(command: list[str], arm: Path) -> dict[str, object]:
    failures: list[str] = []
    passed = 0

    for expression, expected in VALID_CASES:
        result = run([*command, expression], cwd=arm)
        try:
            actual = float(result.stdout.strip())
        except ValueError:
            actual = math.nan
        ok = (
            result.returncode == 0
            and result.stderr == ""
            and math.isfinite(actual)
            and math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12)
        )
        if ok:
            passed += 1
        else:
            failures.append(
                f"valid {expression!r}: rc={result.returncode}, stdout={result.stdout!r}, stderr={result.stderr!r}"
            )

    for expression in INVALID_CASES:
        result = run([*command, expression], cwd=arm)
        ok = result.returncode != 0 and result.stdout == "" and result.stderr.startswith("error:")
        if ok:
            passed += 1
        else:
            failures.append(
                f"invalid {expression!r}: rc={result.returncode}, stdout={result.stdout!r}, stderr={result.stderr!r}"
            )

    for suffix, args in (("missing argument", []), ("extra argument", ["1", "2"])):
        result = run([*command, *args], cwd=arm)
        ok = result.returncode != 0 and result.stdout == "" and result.stderr.startswith("error:")
        if ok:
            passed += 1
        else:
            failures.append(
                f"{suffix}: rc={result.returncode}, stdout={result.stdout!r}, stderr={result.stderr!r}"
            )

    total = len(VALID_CASES) + len(INVALID_CASES) + 2
    return {"passed": passed, "total": total, "perfect": passed == total, "failures": failures}


def test_arm(root: Path, name: str) -> dict[str, object]:
    arm = root / name
    build = arm / "build"
    build.mkdir(exist_ok=True)
    compile_results: dict[str, object] = {}

    for language, command in compile_commands(arm, build).items():
        result = run(command, cwd=arm, timeout=120)
        compile_results[language] = {
            "passed": result.returncode == 0,
            "returncode": result.returncode,
            "stderr": result.stderr,
        }

    language_results: dict[str, object] = {}
    for language, command in runtime_commands(arm, build).items():
        if language in compile_results and not compile_results[language]["passed"]:
            language_results[language] = {
                "passed": 0,
                "total": len(VALID_CASES) + len(INVALID_CASES) + 2,
                "perfect": False,
                "failures": ["compilation failed"],
            }
        else:
            language_results[language] = test_language(command, arm)

    return {
        "compile": compile_results,
        "languages": language_results,
        "perfect": all(item["perfect"] for item in language_results.values()),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--arms", nargs="+")
    args = parser.parse_args()

    selected_arms = args.arms or ARMS
    report = {name: test_arm(args.root, name) for name in selected_arms}
    rendered = json.dumps(report, indent=2, sort_keys=True)
    print(rendered)
    if args.json_out:
        args.json_out.write_text(rendered + "\n")
    return 0 if all(item["perfect"] for item in report.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
